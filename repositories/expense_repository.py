"""Data access for :class:`models.expense.Expense`."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import func

from database.db import db
from models.enums import ExpenseStatus
from models.expense import Expense

from .base_repository import BaseRepository


class ExpenseRepository(BaseRepository[Expense]):
    model = Expense

    def get_filtered(self, status: ExpenseStatus | None = None) -> list[Expense]:
        query = self._base_query()
        if status is not None:
            query = query.filter(Expense.status == status)
        return query.order_by(Expense.created_at.desc()).all()

    def count_by_status(self) -> dict[str, int]:
        rows = (
            self._base_query()
            .with_entities(Expense.status, func.count(Expense.id))
            .group_by(Expense.status)
            .all()
        )
        return {status.value: count for status, count in rows}

    def total_amount(self, status: ExpenseStatus | None = None) -> float:
        query = self._base_query().with_entities(func.coalesce(func.sum(Expense.amount), 0))
        if status is not None:
            query = query.filter(Expense.status == status)
        return float(query.scalar() or 0)

    def count(self, status: ExpenseStatus | None = None) -> int:
        query = self._base_query()
        if status is not None:
            query = query.filter(Expense.status == status)
        return query.count()

    def monthly_totals(self, months: int = 6) -> list[tuple[str, float]]:
        """Return ``[(YYYY-MM, total_amount), ...]`` for the last *months*.

        Aggregation is done in Python so the same code works on SQLite and
        PostgreSQL (date-truncation syntax differs between engines).
        """
        rows = (
            self._base_query()
            .with_entities(Expense.created_at, Expense.amount)
            .filter(Expense.status != ExpenseStatus.CANCELLED)
            .all()
        )
        return _group_by_month(rows, months)

    def next_folio_sequence(self, year: int) -> int:
        """Highest existing sequence number for the given year + 1."""
        prefix = f"EXP-{year}-"
        last = (
            db.session.query(Expense.folio)
            .filter(Expense.folio.like(f"{prefix}%"))
            .order_by(Expense.folio.desc())
            .first()
        )
        if not last:
            return 1
        try:
            return int(last[0].split("-")[-1]) + 1
        except (ValueError, IndexError):  # pragma: no cover - defensive
            return self.count() + 1


def _group_by_month(rows, months: int) -> list[tuple[str, float]]:
    """Shared monthly bucketing helper for expenses and payments."""
    from collections import OrderedDict

    buckets: "OrderedDict[str, float]" = OrderedDict()
    # Pre-seed the last N months so the chart shows empty months too.
    now = datetime.utcnow()
    year, month = now.year, now.month
    seq = []
    for _ in range(months):
        seq.append(f"{year:04d}-{month:02d}")
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    for key in reversed(seq):
        buckets[key] = 0.0

    for created_at, amount in rows:
        if created_at is None:
            continue
        key = f"{created_at.year:04d}-{created_at.month:02d}"
        if key in buckets:
            buckets[key] += float(amount)
    return list(buckets.items())
