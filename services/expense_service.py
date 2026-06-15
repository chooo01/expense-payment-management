"""Expense service — owns the expense state machine and invariants.

Business rules implemented here (from the spec):
    * An expense starts in PENDING.
    * It can be APPROVED (only from PENDING).
    * It can be CANCELLED (from PENDING or APPROVED *without* active payments).
    * A CANCELLED expense can never be reactivated (terminal state).
    * An APPROVED expense can generate payments (handled by PaymentService).

Every transition is recorded in the status-history audit log, and the service
owns the transaction boundary (commit/rollback).
"""
from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation

from database.db import db
from models.enums import EntityType, ExpenseStatus, PaymentStatus
from models.expense import Expense
from repositories.expense_repository import ExpenseRepository
from repositories.status_history_repository import StatusHistoryRepository

from .exceptions import BusinessRuleError, NotFoundError, ValidationError

logger = logging.getLogger(__name__)

# Allowed transitions for the expense state machine. CANCELLED is terminal
# (empty target set), enforcing "a cancelled expense can never be reactivated".
# PAID -> APPROVED is reachable *only* internally, when an executed payment is
# reversed (cancelled); there is no public command that performs it.
_ALLOWED_TRANSITIONS: dict[ExpenseStatus, set[ExpenseStatus]] = {
    ExpenseStatus.PENDING: {ExpenseStatus.APPROVED, ExpenseStatus.CANCELLED},
    ExpenseStatus.APPROVED: {ExpenseStatus.CANCELLED, ExpenseStatus.PAID},
    ExpenseStatus.CANCELLED: set(),
    ExpenseStatus.PAID: {ExpenseStatus.APPROVED},
}


class ExpenseService:
    def __init__(
        self,
        expense_repository: ExpenseRepository | None = None,
        history_repository: StatusHistoryRepository | None = None,
    ) -> None:
        self.expenses = expense_repository or ExpenseRepository()
        self.history = history_repository or StatusHistoryRepository()

    # --- Queries ------------------------------------------------------------
    def list_expenses(self, status: ExpenseStatus | None = None) -> list[Expense]:
        return self.expenses.get_filtered(status=status)

    def get_or_404(self, expense_id: int) -> Expense:
        expense = self.expenses.get_by_id(expense_id)
        if expense is None:
            raise NotFoundError(f"Gasto {expense_id} no encontrado.")
        return expense

    # --- Commands -----------------------------------------------------------
    def create_expense(
        self, *, description: str, amount, created_by: int
    ) -> Expense:
        description = (description or "").strip()
        if not description:
            raise ValidationError("La descripción es obligatoria.")
        amount_dec = self._validate_amount(amount)

        expense = Expense(
            folio=self._generate_folio(),
            description=description,
            amount=amount_dec,
            status=ExpenseStatus.PENDING,
            created_by=created_by,
        )
        self.expenses.add(expense)
        self._record_transition(expense, None, ExpenseStatus.PENDING, created_by)
        db.session.commit()
        logger.info("Expense %s created by user=%s amount=%s", expense.folio, created_by, amount_dec)
        return expense

    def approve_expense(self, expense_id: int, *, user_id: int) -> Expense:
        expense = self.get_or_404(expense_id)
        self._transition(expense, ExpenseStatus.APPROVED, user_id)
        expense.approved_by = user_id
        db.session.commit()
        logger.info("Expense %s approved by user=%s", expense.folio, user_id)
        return expense

    def cancel_expense(self, expense_id: int, *, user_id: int) -> Expense:
        expense = self.get_or_404(expense_id)

        # Guard: cannot cancel an expense that already has non-cancelled payments.
        active_payments = [
            p for p in expense.payments if p.status != PaymentStatus.CANCELLED
        ]
        if active_payments:
            raise BusinessRuleError(
                "No se puede cancelar un gasto con pagos activos. "
                "Cancele primero los pagos asociados."
            )

        self._transition(expense, ExpenseStatus.CANCELLED, user_id)
        db.session.commit()
        logger.info("Expense %s cancelled by user=%s", expense.folio, user_id)
        return expense

    def mark_paid_if_settled(self, expense: Expense, *, user_id: int | None) -> None:
        """Promote an APPROVED expense to PAID once fully covered.

        Called by the payment service after a payment is executed. Does *not*
        commit — it participates in the caller's transaction.
        """
        if (
            expense.status == ExpenseStatus.APPROVED
            and expense.remaining_amount() <= Decimal("0.00")
        ):
            self._transition(expense, ExpenseStatus.PAID, user_id, commit=False)

    def reopen_if_needed(self, expense: Expense, *, user_id: int | None) -> None:
        """Revert a PAID expense to APPROVED when it is no longer fully covered.

        Triggered by the payment service when an executed payment is reversed.
        Participates in the caller's transaction (no commit).
        """
        if (
            expense.status == ExpenseStatus.PAID
            and expense.remaining_amount() > Decimal("0.00")
        ):
            self._transition(expense, ExpenseStatus.APPROVED, user_id, commit=False)

    # --- Internals ----------------------------------------------------------
    def _transition(
        self,
        expense: Expense,
        new_status: ExpenseStatus,
        user_id: int | None,
        *,
        commit: bool = False,
    ) -> None:
        current = expense.status
        if new_status not in _ALLOWED_TRANSITIONS.get(current, set()):
            raise BusinessRuleError(
                f"Transición inválida de gasto {current.label} → {new_status.label}."
            )
        self._record_transition(expense, current, new_status, user_id)
        expense.status = new_status
        if commit:
            db.session.commit()

    def _record_transition(self, expense, previous, new_status, user_id) -> None:
        self.history.record(
            entity_type=EntityType.EXPENSE,
            entity_id=expense.id,
            previous_status=previous.value if previous else None,
            new_status=new_status.value,
            changed_by=user_id,
        )

    @staticmethod
    def _validate_amount(amount) -> Decimal:
        try:
            value = Decimal(str(amount)).quantize(Decimal("0.01"))
        except (InvalidOperation, TypeError, ValueError):
            raise ValidationError("El monto no es un número válido.")
        if value <= Decimal("0.00"):
            raise ValidationError("El monto debe ser mayor que cero.")
        return value

    def _generate_folio(self) -> str:
        year = datetime.utcnow().year
        seq = self.expenses.next_folio_sequence(year)
        return f"EXP-{year}-{seq:06d}"
