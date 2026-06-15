"""Payment model — disburses (part of) an approved expense from an account."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime
from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.db import db

from .base import SoftDeleteMixin, TimestampMixin
from .enums import PaymentStatus


class Payment(SoftDeleteMixin, TimestampMixin, db.Model):
    """A payment generated from an approved expense.

    State machine (enforced in :mod:`services.payment_service`):
        PENDING -> APPROVED -> PAID   (PAID debits the bank account balance)
        PENDING/APPROVED -> CANCELLED (terminal)

    Partial payments are supported: several payments may point to one expense
    as long as their combined amount never exceeds the expense amount.
    """

    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    payment_folio: Mapped[str] = mapped_column(
        String(30), unique=True, nullable=False, index=True
    )
    expense_id: Mapped[int] = mapped_column(
        ForeignKey("expenses.id"), nullable=False, index=True
    )
    bank_account_id: Mapped[int] = mapped_column(
        ForeignKey("bank_accounts.id"), nullable=False, index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(
        SAEnum(PaymentStatus, native_enum=False, length=20),
        default=PaymentStatus.PENDING,
        nullable=False,
        index=True,
    )
    # Set when the payment is actually executed (status -> PAID).
    payment_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )

    # Relationships
    expense: Mapped["Expense"] = relationship(  # noqa: F821
        back_populates="payments"
    )
    bank_account: Mapped["BankAccount"] = relationship(  # noqa: F821
        back_populates="payments"
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "payment_folio": self.payment_folio,
            "expense_id": self.expense_id,
            "expense_folio": self.expense.folio if self.expense else None,
            "bank_account_id": self.bank_account_id,
            "bank_account_name": (
                self.bank_account.account_name if self.bank_account else None
            ),
            "amount": float(self.amount),
            "status": self.status.value,
            "status_label": self.status.label,
            "payment_date": (
                self.payment_date.isoformat() if self.payment_date else None
            ),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Payment {self.payment_folio} {self.status.value} {self.amount}>"
