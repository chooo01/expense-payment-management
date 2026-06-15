"""Bank-account movement model — ledger of balance changes.

Required by the business rule *"Debe mantenerse historial de movimientos"*.
Although not in the original five-table list, an explicit ledger is the
professional way to keep the bank balance auditable and reconcilable: every
debit/credit records the running balance after the movement.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime
from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.db import db

from .base import utcnow
from .enums import MovementType


class BankAccountMovement(db.Model):
    """An immutable ledger entry for a bank account."""

    __tablename__ = "bank_account_movements"

    id: Mapped[int] = mapped_column(primary_key=True)
    bank_account_id: Mapped[int] = mapped_column(
        ForeignKey("bank_accounts.id"), nullable=False, index=True
    )
    payment_id: Mapped[int | None] = mapped_column(
        ForeignKey("payments.id"), nullable=True, index=True
    )
    movement_type: Mapped[MovementType] = mapped_column(
        SAEnum(MovementType, native_enum=False, length=10), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    # Balance snapshot *after* applying this movement (for easy reconciliation).
    balance_after: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False, index=True
    )

    bank_account: Mapped["BankAccount"] = relationship(  # noqa: F821
        back_populates="movements"
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "bank_account_id": self.bank_account_id,
            "payment_id": self.payment_id,
            "movement_type": self.movement_type.value,
            "amount": float(self.amount),
            "balance_after": float(self.balance_after),
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<Movement {self.movement_type.value} {self.amount} "
            f"acct={self.bank_account_id}>"
        )
