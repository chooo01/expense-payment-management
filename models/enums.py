"""Domain enumerations.

Centralizing the status vocabularies here keeps the state machines explicit
and lets every layer (models, services, templates, API) share one source of
truth. We subclass ``str`` so the values serialize cleanly to JSON and persist
as readable strings in the database.
"""
from __future__ import annotations

import enum


class ExpenseStatus(str, enum.Enum):
    """Lifecycle of an expense.

    PENDING --> APPROVED --> PAID
       |            |
       v            v
    CANCELLED   CANCELLED   (CANCELLED is terminal: never reactivated)
    """

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    CANCELLED = "CANCELLED"
    PAID = "PAID"  # Derived: set when the approved amount is fully paid.

    @property
    def label(self) -> str:
        return {
            "PENDING": "Pendiente",
            "APPROVED": "Aprobado",
            "CANCELLED": "Cancelado",
            "PAID": "Pagado",
        }[self.value]


class PaymentStatus(str, enum.Enum):
    """Lifecycle of a payment.

    PENDING --> APPROVED --> PAID   (PAID debits the bank account)
       |            |
       v            v
    CANCELLED   CANCELLED           (CANCELLED is terminal)
    """

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    PAID = "PAID"
    CANCELLED = "CANCELLED"

    @property
    def label(self) -> str:
        return {
            "PENDING": "Pendiente",
            "APPROVED": "Aprobado",
            "PAID": "Pagado",
            "CANCELLED": "Cancelado",
        }[self.value]


class EntityType(str, enum.Enum):
    """Identifies the audited entity in the status-history table."""

    EXPENSE = "EXPENSE"
    PAYMENT = "PAYMENT"


class MovementType(str, enum.Enum):
    """Direction of a bank-account movement (ledger entry)."""

    DEBIT = "DEBIT"    # Money leaving the account (a payment was executed).
    CREDIT = "CREDIT"  # Money returning (e.g. reversal of a paid payment).
