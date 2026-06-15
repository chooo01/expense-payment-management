"""Generic repository.

The repository layer isolates persistence concerns (queries, sessions) from
business logic. Services depend on repositories rather than touching the ORM
session directly, which keeps services testable and the data-access patterns
consistent. Repositories *stage* changes (``db.session.add``) and *flush* to
obtain generated ids, but the **service layer owns the transaction boundary**
(``commit`` / ``rollback``) so a multi-step operation is atomic.
"""
from __future__ import annotations

from typing import Generic, Type, TypeVar

from database.db import db
from models.base import SoftDeleteMixin

T = TypeVar("T", bound=db.Model)


class BaseRepository(Generic[T]):
    """CRUD helpers shared by every concrete repository."""

    model: Type[T]

    def __init__(self, model: Type[T] | None = None) -> None:
        if model is not None:
            self.model = model

    # --- Reads --------------------------------------------------------------
    def _base_query(self):
        """Query that automatically hides soft-deleted rows when applicable."""
        query = db.session.query(self.model)
        if issubclass(self.model, SoftDeleteMixin):
            query = query.filter(self.model.is_deleted.is_(False))
        return query

    def get_by_id(self, entity_id: int) -> T | None:
        return self._base_query().filter(self.model.id == entity_id).first()

    def get_all(self) -> list[T]:
        return self._base_query().all()

    # --- Writes -------------------------------------------------------------
    def add(self, entity: T) -> T:
        """Stage an insert and flush so the generated id is available."""
        db.session.add(entity)
        db.session.flush()
        return entity

    def delete(self, entity: T) -> None:
        """Soft-delete when supported, otherwise hard-delete."""
        if isinstance(entity, SoftDeleteMixin):
            entity.soft_delete()
        else:
            db.session.delete(entity)
