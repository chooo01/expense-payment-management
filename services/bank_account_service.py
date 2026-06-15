"""Bank account service — account CRUD and the balance ledger.

Balance changes are *only* performed here, always paired with a
:class:`BankAccountMovement` entry, so the ledger and the balance can never
drift apart. These methods do not commit; the payment service composes them
inside a single transaction.
"""
from __future__ import annotations

import logging
from decimal import Decimal, InvalidOperation

from models.bank_account import BankAccount
from models.bank_account_movement import BankAccountMovement
from models.enums import MovementType
from repositories.bank_account_repository import BankAccountRepository

from .exceptions import BusinessRuleError, NotFoundError, ValidationError

logger = logging.getLogger(__name__)


class BankAccountService:
    def __init__(self, repository: BankAccountRepository | None = None) -> None:
        self.accounts = repository or BankAccountRepository()

    # --- Queries ------------------------------------------------------------
    def list_accounts(self, only_active: bool = False) -> list[BankAccount]:
        return self.accounts.get_active() if only_active else self.accounts.get_all()

    def get_or_404(self, account_id: int) -> BankAccount:
        account = self.accounts.get_by_id(account_id)
        if account is None:
            raise NotFoundError(f"Cuenta bancaria {account_id} no encontrada.")
        return account

    def get_movements(self, account_id: int) -> list[BankAccountMovement]:
        self.get_or_404(account_id)
        return self.accounts.get_movements(account_id)

    # --- Commands -----------------------------------------------------------
    def create_account(
        self, *, account_name: str, bank_name: str, account_number: str, initial_balance
    ) -> BankAccount:
        from database.db import db

        account_name = (account_name or "").strip()
        bank_name = (bank_name or "").strip()
        account_number = (account_number or "").strip()
        if not (account_name and bank_name and account_number):
            raise ValidationError("Nombre, banco y número de cuenta son obligatorios.")
        if self.accounts.get_by_number(account_number):
            raise ValidationError("Ya existe una cuenta con ese número.")

        balance = self._validate_amount(initial_balance, allow_zero=True)
        account = BankAccount(
            account_name=account_name,
            bank_name=bank_name,
            account_number=account_number,
            current_balance=balance,
            active=True,
        )
        self.accounts.add(account)

        if balance > Decimal("0.00"):
            self._add_movement(
                account, MovementType.CREDIT, balance, "Saldo inicial", payment_id=None
            )
        db.session.commit()
        logger.info("Bank account %r created with balance=%s", account_name, balance)
        return account

    def debit(self, account: BankAccount, amount: Decimal, *, payment_id: int, description: str):
        """Subtract from the balance (payment executed). No commit."""
        if amount > account.current_balance:
            raise BusinessRuleError(
                "El pago excede el saldo disponible de la cuenta "
                f"({account.current_balance})."
            )
        account.current_balance = (account.current_balance - amount).quantize(Decimal("0.01"))
        return self._add_movement(
            account, MovementType.DEBIT, amount, description, payment_id=payment_id
        )

    def credit(self, account: BankAccount, amount: Decimal, *, payment_id: int, description: str):
        """Add to the balance (reversal of an executed payment). No commit."""
        account.current_balance = (account.current_balance + amount).quantize(Decimal("0.01"))
        return self._add_movement(
            account, MovementType.CREDIT, amount, description, payment_id=payment_id
        )

    # --- Internals ----------------------------------------------------------
    def _add_movement(self, account, movement_type, amount, description, *, payment_id):
        movement = BankAccountMovement(
            bank_account_id=account.id,
            payment_id=payment_id,
            movement_type=movement_type,
            amount=amount,
            balance_after=account.current_balance,
            description=description,
        )
        return self.accounts.add_movement(movement)

    @staticmethod
    def _validate_amount(amount, *, allow_zero: bool = False) -> Decimal:
        try:
            value = Decimal(str(amount)).quantize(Decimal("0.01"))
        except (InvalidOperation, TypeError, ValueError):
            raise ValidationError("El monto no es un número válido.")
        if value < Decimal("0.00") or (value == Decimal("0.00") and not allow_zero):
            raise ValidationError("El monto debe ser mayor o igual que cero.")
        return value
