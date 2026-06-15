"""Data access for bank accounts and their movement ledger."""
from __future__ import annotations

from models.bank_account import BankAccount
from models.bank_account_movement import BankAccountMovement

from .base_repository import BaseRepository


class BankAccountRepository(BaseRepository[BankAccount]):
    model = BankAccount

    def get_active(self) -> list[BankAccount]:
        return (
            self._base_query()
            .filter(BankAccount.active.is_(True))
            .order_by(BankAccount.account_name)
            .all()
        )

    def get_by_number(self, account_number: str) -> BankAccount | None:
        return (
            self._base_query()
            .filter(BankAccount.account_number == account_number)
            .first()
        )

    # --- Movement ledger ----------------------------------------------------
    def add_movement(self, movement: BankAccountMovement) -> BankAccountMovement:
        from database.db import db

        db.session.add(movement)
        db.session.flush()
        return movement

    def get_movements(self, bank_account_id: int) -> list[BankAccountMovement]:
        from database.db import db

        return (
            db.session.query(BankAccountMovement)
            .filter(BankAccountMovement.bank_account_id == bank_account_id)
            .order_by(BankAccountMovement.created_at.desc())
            .all()
        )
