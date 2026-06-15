"""Reusable model mix-ins.

``TimestampMixin`` and ``SoftDeleteMixin`` keep cross-cutting columns
(created/updated timestamps and logical deletion) in one place so every table
behaves consistently and we honour the "Soft Delete where applicable"
requirement without copy-pasting columns.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column


def utcnow() -> datetime:
    """Timezone-aware UTC now (avoids the deprecated naive ``utcnow``)."""
    return datetime.now(timezone.utc)


class TimestampMixin:
    """Adds ``created_at`` / ``updated_at`` audit columns."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class SoftDeleteMixin:
    """Adds an ``is_deleted`` flag for logical deletion.

    Repositories filter ``is_deleted == False`` by default so soft-deleted
    rows disappear from normal queries while remaining available for audit.
    """

    is_deleted: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True
    )

    def soft_delete(self) -> None:
        self.is_deleted = True
