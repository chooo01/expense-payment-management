"""User model — application accounts used for login and auditing."""
from __future__ import annotations

from flask_login import UserMixin
from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.db import db

from .base import TimestampMixin


class User(UserMixin, TimestampMixin, db.Model):
    """An authenticated user.

    Inherits Flask-Login's :class:`UserMixin` (``is_authenticated`` etc.).
    Passwords are never stored in clear text — only the bcrypt hash lives in
    ``password_hash`` (see :class:`services.auth_service.AuthService`).
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(
        String(80), unique=True, nullable=False, index=True
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Reverse relationships for auditing (who created / approved what).
    created_expenses: Mapped[list["Expense"]] = relationship(  # noqa: F821
        back_populates="creator", foreign_keys="Expense.created_by"
    )

    # Flask-Login uses ``is_active`` to block disabled accounts.
    @property
    def is_active(self) -> bool:  # type: ignore[override]
        return bool(self.active)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "username": self.username,
            "active": self.active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<User {self.id} {self.username!r}>"
