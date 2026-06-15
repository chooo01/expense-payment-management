"""Expense model — a company expense that flows through an approval cycle."""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.db import db

from .base import SoftDeleteMixin, TimestampMixin
from .enums import ExpenseStatus, PaymentStatus


class Expense(SoftDeleteMixin, TimestampMixin, db.Model):
    """An expense request.

    State machine (enforced in :mod:`services.expense_service`):
        PENDING -> APPROVED -> PAID
        PENDING/APPROVED -> CANCELLED  (terminal; never reactivated)

    The monetary amount is ``Numeric(18, 2)``. ``folio`` is a human-readable,
    unique business identifier (e.g. ``EXP-2026-000001``).
    """

    __tablename__ = "expenses"

    id: Mapped[int] = mapped_column(primary_key=True)
    folio: Mapped[str] = mapped_column(
        String(30), unique=True, nullable=False, index=True
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    status: Mapped[ExpenseStatus] = mapped_column(
        SAEnum(ExpenseStatus, native_enum=False, length=20),
        default=ExpenseStatus.PENDING,
        nullable=False,
        index=True,
    )

    created_by: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    approved_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )

    # Relationships
    creator: Mapped["User"] = relationship(  # noqa: F821
        foreign_keys=[created_by], back_populates="created_expenses"
    )
    approver: Mapped["User | None"] = relationship(  # noqa: F821
        foreign_keys=[approved_by]
    )
    payments: Mapped[list["Payment"]] = relationship(  # noqa: F821
        back_populates="expense"
    )

    # --- Derived monetary helpers ------------------------------------------
    def paid_amount(self) -> Decimal:
        """Sum of payments that consume the expense (not cancelled)."""
        total = sum(
            (p.amount for p in self.payments if p.status != PaymentStatus.CANCELLED),
            Decimal("0.00"),
        )
        return Decimal(total).quantize(Decimal("0.01"))

    def remaining_amount(self) -> Decimal:
        """Amount still available to be covered by new payments."""
        return (self.amount - self.paid_amount()).quantize(Decimal("0.01"))

    def to_dict(self, include_payments: bool = False) -> dict:
        data = {
            "id": self.id,
            "folio": self.folio,
            "description": self.description,
            "amount": float(self.amount),
            "paid_amount": float(self.paid_amount()),
            "remaining_amount": float(self.remaining_amount()),
            "status": self.status.value,
            "status_label": self.status.label,
            "created_by": self.created_by,
            "approved_by": self.approved_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_payments:
            data["payments"] = [p.to_dict() for p in self.payments]
        return data

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Expense {self.folio} {self.status.value} {self.amount}>"
