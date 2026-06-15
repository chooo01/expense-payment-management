"""Status-history model — immutable audit log of every state transition."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from database.db import db

from .base import utcnow
from .enums import EntityType


class StatusHistory(db.Model):
    """One row per state change of an expense or payment.

    This table is *append-only*: rows are never updated or deleted, giving a
    tamper-evident audit trail of who changed what and when. ``entity_type`` +
    ``entity_id`` form a polymorphic reference so a single table audits both
    expenses and payments.
    """

    __tablename__ = "status_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_type: Mapped[EntityType] = mapped_column(
        SAEnum(EntityType, native_enum=False, length=20), nullable=False, index=True
    )
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    previous_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    new_status: Mapped[str] = mapped_column(String(20), nullable=False)
    changed_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False, index=True
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "entity_type": self.entity_type.value,
            "entity_id": self.entity_id,
            "previous_status": self.previous_status,
            "new_status": self.new_status,
            "changed_by": self.changed_by,
            "changed_at": self.changed_at.isoformat() if self.changed_at else None,
        }

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<StatusHistory {self.entity_type.value}#{self.entity_id} "
            f"{self.previous_status}->{self.new_status}>"
        )
