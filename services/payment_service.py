"""Payment service — orchestrates payments, expenses and bank balances.

Business rules implemented here (from the spec):
    * Payments must originate from an APPROVED expense.
    * Generated on demand (the "Generar Pago" button calls ``generate_payment``).
    * Partial payments supported: many payments per expense.
    * Duplicate / over-payment prevented: Σ(active payments) ≤ expense.amount.
    * Payments can be APPROVED, marked PAID (executed) and CANCELLED.
    * A payment cannot exceed the bank account's available balance.
    * Executing a payment debits the balance and writes a ledger movement.
    * Cancelling an *executed* payment reverses the balance (credit movement).

This service owns multi-table transactions (payment + expense + account +
ledger + audit) and commits them atomically.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from database.db import db
from models.enums import EntityType, PaymentStatus
from models.payment import Payment
from repositories.payment_repository import PaymentRepository
from repositories.status_history_repository import StatusHistoryRepository

from .bank_account_service import BankAccountService
from .exceptions import BusinessRuleError, NotFoundError, ValidationError
from .expense_service import ExpenseService

logger = logging.getLogger(__name__)

_ALLOWED_TRANSITIONS: dict[PaymentStatus, set[PaymentStatus]] = {
    PaymentStatus.PENDING: {PaymentStatus.APPROVED, PaymentStatus.CANCELLED},
    PaymentStatus.APPROVED: {PaymentStatus.PAID, PaymentStatus.CANCELLED},
    PaymentStatus.PAID: {PaymentStatus.CANCELLED},  # cancellation = reversal
    PaymentStatus.CANCELLED: set(),
}


class PaymentService:
    def __init__(
        self,
        payment_repository: PaymentRepository | None = None,
        history_repository: StatusHistoryRepository | None = None,
        expense_service: ExpenseService | None = None,
        bank_account_service: BankAccountService | None = None,
    ) -> None:
        self.payments = payment_repository or PaymentRepository()
        self.history = history_repository or StatusHistoryRepository()
        self.expenses = expense_service or ExpenseService()
        self.bank_accounts = bank_account_service or BankAccountService()

    # --- Queries ------------------------------------------------------------
    def list_payments(
        self, status: PaymentStatus | None = None, expense_id: int | None = None
    ) -> list[Payment]:
        return self.payments.get_filtered(status=status, expense_id=expense_id)

    def get_or_404(self, payment_id: int) -> Payment:
        payment = self.payments.get_by_id(payment_id)
        if payment is None:
            raise NotFoundError(f"Pago {payment_id} no encontrado.")
        return payment

    # --- Commands -----------------------------------------------------------
    def generate_payment(
        self, *, expense_id: int, bank_account_id: int, amount, user_id: int
    ) -> Payment:
        """Create a PENDING payment from an approved expense ("Generar Pago")."""
        from models.enums import ExpenseStatus

        expense = self.expenses.get_or_404(expense_id)
        if expense.status != ExpenseStatus.APPROVED:
            raise BusinessRuleError(
                "Solo los gastos APROBADOS pueden generar pagos."
            )

        account = self.bank_accounts.get_or_404(bank_account_id)
        if not account.active:
            raise BusinessRuleError("La cuenta bancaria está inactiva.")

        amount_dec = self._validate_amount(amount)
        remaining = expense.remaining_amount()
        if remaining <= Decimal("0.00"):
            raise BusinessRuleError("El gasto ya está totalmente pagado.")
        if amount_dec > remaining:
            # Prevents duplicate / over-payment (partial payments allowed).
            raise BusinessRuleError(
                f"El monto excede el saldo pendiente del gasto ({remaining})."
            )

        payment = Payment(
            payment_folio=self._generate_folio(),
            expense_id=expense.id,
            bank_account_id=account.id,
            amount=amount_dec,
            status=PaymentStatus.PENDING,
            created_by=user_id,
        )
        self.payments.add(payment)
        self._record_transition(payment, None, PaymentStatus.PENDING, user_id)
        db.session.commit()
        logger.info(
            "Payment %s generated for expense=%s amount=%s account=%s",
            payment.payment_folio, expense.folio, amount_dec, account.id,
        )
        return payment

    def approve_payment(self, payment_id: int, *, user_id: int) -> Payment:
        payment = self.get_or_404(payment_id)
        self._transition(payment, PaymentStatus.APPROVED, user_id)
        db.session.commit()
        logger.info("Payment %s approved by user=%s", payment.payment_folio, user_id)
        return payment

    def execute_payment(self, payment_id: int, *, user_id: int) -> Payment:
        """Mark an APPROVED payment as PAID: debit the account and settle.

        All side effects (transition, balance debit, ledger movement, expense
        settlement) happen in one transaction; any failure rolls everything
        back via the route/error layer.
        """
        payment = self.get_or_404(payment_id)
        if payment.status != PaymentStatus.APPROVED:
            raise BusinessRuleError(
                "Solo los pagos APROBADOS pueden marcarse como pagados."
            )

        account = self.bank_accounts.get_or_404(payment.bank_account_id)
        # debit() raises BusinessRuleError if the amount exceeds the balance.
        self.bank_accounts.debit(
            account,
            payment.amount,
            payment_id=payment.id,
            description=f"Pago {payment.payment_folio} (gasto {payment.expense.folio})",
        )
        self._transition(payment, PaymentStatus.PAID, user_id)
        payment.payment_date = datetime.now(timezone.utc)

        # Promote the expense to PAID when fully covered.
        self.expenses.mark_paid_if_settled(payment.expense, user_id=user_id)

        db.session.commit()
        logger.info(
            "Payment %s executed by user=%s; account=%s new_balance=%s",
            payment.payment_folio, user_id, account.id, account.current_balance,
        )
        return payment

    def cancel_payment(self, payment_id: int, *, user_id: int) -> Payment:
        payment = self.get_or_404(payment_id)
        was_paid = payment.status == PaymentStatus.PAID

        self._transition(payment, PaymentStatus.CANCELLED, user_id)

        if was_paid:
            # Reverse the debit: credit the money back and reopen the expense.
            account = self.bank_accounts.get_or_404(payment.bank_account_id)
            self.bank_accounts.credit(
                account,
                payment.amount,
                payment_id=payment.id,
                description=f"Reversa de pago {payment.payment_folio}",
            )
            self.expenses.reopen_if_needed(payment.expense, user_id=user_id)

        db.session.commit()
        logger.info(
            "Payment %s cancelled by user=%s (reversed=%s)",
            payment.payment_folio, user_id, was_paid,
        )
        return payment

    # --- Internals ----------------------------------------------------------
    def _transition(self, payment, new_status, user_id) -> None:
        current = payment.status
        if new_status not in _ALLOWED_TRANSITIONS.get(current, set()):
            raise BusinessRuleError(
                f"Transición inválida de pago {current.label} → {new_status.label}."
            )
        self._record_transition(payment, current, new_status, user_id)
        payment.status = new_status

    def _record_transition(self, payment, previous, new_status, user_id) -> None:
        self.history.record(
            entity_type=EntityType.PAYMENT,
            entity_id=payment.id,
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
        seq = self.payments.next_folio_sequence(year)
        return f"PAY-{year}-{seq:06d}"
