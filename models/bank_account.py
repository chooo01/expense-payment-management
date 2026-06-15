"""Bank account model — the source of funds for payments."""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Boolean, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.db import db

from .base import SoftDeleteMixin, TimestampMixin


class BankAccount(SoftDeleteMixin, TimestampMixin, db.Model):
    """A company bank account.

    ``current_balance`` is stored as ``Numeric`` (not float) to avoid
    floating-point rounding errors on monetary values. The balance is mutated
    only by the payment service when a payment is *executed*, and every change
    is mirrored in :class:`BankAccountMovement` for a full audit trail.
    """

    __tablename__ = "bank_accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_name: Mapped[str] = mapped_column(String(120), nullable=False)
    bank_name: Mapped[str] = mapped_column(String(120), nullable=False)
    account_number: Mapped[str] = mapped_column(
        String(40), unique=True, nullable=False, index=True
    )
    current_balance: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), default=Decimal("0.00"), nullable=False
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    payments: Mapped[list["Payment"]] = relationship(  # noqa: F821
        back_populates="bank_account"
    )
    movements: Mapped[list["BankAccountMovement"]] = relationship(  # noqa: F821
        back_populates="bank_account",
        order_by="BankAccountMovement.created_at.desc()",
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "account_name": self.account_name,
            "bank_name": self.bank_name,
            # Mask all but the last 4 digits in API responses.
            "account_number": self._masked_number(),
            "current_balance": float(self.current_balance),
            "active": self.active,
        }

    def _masked_number(self) -> str:
        n = self.account_number or ""
        return ("*" * max(0, len(n) - 4)) + n[-4:] if n else ""

    def __repr__(self) -> str:  # pragma: no cover
        return f"<BankAccount {self.id} {self.account_name!r} bal={self.current_balance}>"
