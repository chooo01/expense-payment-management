"""Data access for the append-only :class:`models.status_history.StatusHistory`."""
from __future__ import annotations

from database.db import db
from models.enums import EntityType
from models.status_history import StatusHistory

from .base_repository import BaseRepository


class StatusHistoryRepository(BaseRepository[StatusHistory]):
    model = StatusHistory

    def record(
        self,
        *,
        entity_type: EntityType,
        entity_id: int,
        previous_status: str | None,
        new_status: str,
        changed_by: int | None,
    ) -> StatusHistory:
        """Append a transition entry (caller controls the commit)."""
        entry = StatusHistory(
            entity_type=entity_type,
            entity_id=entity_id,
            previous_status=previous_status,
            new_status=new_status,
            changed_by=changed_by,
        )
        db.session.add(entry)
        db.session.flush()
        return entry

    def for_entity(self, entity_type: EntityType, entity_id: int) -> list[StatusHistory]:
        return (
            db.session.query(StatusHistory)
            .filter(
                StatusHistory.entity_type == entity_type,
                StatusHistory.entity_id == entity_id,
            )
            .order_by(StatusHistory.changed_at.asc())
            .all()
        )
