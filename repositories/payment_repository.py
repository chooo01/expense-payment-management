"""Data access for :class:`models.payment.Payment`."""
from __future__ import annotations

from sqlalchemy import func

from database.db import db
from models.enums import PaymentStatus
from models.payment import Payment

from .base_repository import BaseRepository
from .expense_repository import _group_by_month


class PaymentRepository(BaseRepository[Payment]):
    model = Payment

    def get_filtered(
        self,
        status: PaymentStatus | None = None,
        expense_id: int | None = None,
    ) -> list[Payment]:
        query = self._base_query()
        if status is not None:
            query = query.filter(Payment.status == status)
        if expense_id is not None:
            query = query.filter(Payment.expense_id == expense_id)
        return query.order_by(Payment.created_at.desc()).all()

    def for_expense(self, expense_id: int) -> list[Payment]:
        return self.get_filtered(expense_id=expense_id)

    def count_by_status(self) -> dict[str, int]:
        rows = (
            self._base_query()
            .with_entities(Payment.status, func.count(Payment.id))
            .group_by(Payment.status)
            .all()
        )
        return {status.value: count for status, count in rows}

    def total_amount(self, status: PaymentStatus | None = None) -> float:
        query = self._base_query().with_entities(func.coalesce(func.sum(Payment.amount), 0))
        if status is not None:
            query = query.filter(Payment.status == status)
        return float(query.scalar() or 0)

    def count(self, status: PaymentStatus | None = None) -> int:
        query = self._base_query()
        if status is not None:
            query = query.filter(Payment.status == status)
        return query.count()

    def consumption_by_account(self) -> list[tuple[int, str, float]]:
        """Total executed (PAID) amount grouped by bank account."""
        from models.bank_account import BankAccount

        rows = (
            self._base_query()
            .join(BankAccount, Payment.bank_account_id == BankAccount.id)
            .with_entities(
                BankAccount.id,
                BankAccount.account_name,
                func.coalesce(func.sum(Payment.amount), 0),
            )
            .filter(Payment.status == PaymentStatus.PAID)
            .group_by(BankAccount.id, BankAccount.account_name)
            .all()
        )
        return [(rid, name, float(total)) for rid, name, total in rows]

    def monthly_totals(self, months: int = 6) -> list[tuple[str, float]]:
        rows = (
            self._base_query()
            .with_entities(Payment.created_at, Payment.amount)
            .filter(Payment.status != PaymentStatus.CANCELLED)
            .all()
        )
        return _group_by_month(rows, months)

    def next_folio_sequence(self, year: int) -> int:
        prefix = f"PAY-{year}-"
        last = (
            db.session.query(Payment.payment_folio)
            .filter(Payment.payment_folio.like(f"{prefix}%"))
            .order_by(Payment.payment_folio.desc())
            .first()
        )
        if not last:
            return 1
        try:
            return int(last[0].split("-")[-1]) + 1
        except (ValueError, IndexError):  # pragma: no cover - defensive
            return self.count() + 1
