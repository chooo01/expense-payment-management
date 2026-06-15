"""Marshmallow schema layer.

Separated from the API controllers (Clean Architecture): schemas define the
*contract* (serialization + validation + OpenAPI documentation), controllers
orchestrate, services hold business logic. Schemas are reused across endpoints
so OpenAPI emits a single component per entity (no duplication).
"""
from .auth import LoginSchema, TokenSchema
from .bank_account import (
    BankAccountCreateSchema,
    BankAccountDetailSchema,
    BankAccountListSchema,
    BankAccountMovementSchema,
    BankAccountSchema,
)
from .common import EnumField, ErrorSchema, ValidationErrorSchema
from .dashboard import (
    AccountBalanceSchema,
    ChartsSchema,
    ConsumptionSchema,
    DashboardSchema,
    KpisSchema,
)
from .expense import (
    ExpenseCreateSchema,
    ExpenseDetailSchema,
    ExpenseListSchema,
    ExpenseQuerySchema,
    ExpenseSchema,
)
from .payment import (
    PaymentCreateSchema,
    PaymentListSchema,
    PaymentQuerySchema,
    PaymentSchema,
)

__all__ = [
    "EnumField",
    "ErrorSchema",
    "ValidationErrorSchema",
    "LoginSchema",
    "TokenSchema",
    "ExpenseSchema",
    "ExpenseDetailSchema",
    "ExpenseListSchema",
    "ExpenseQuerySchema",
    "ExpenseCreateSchema",
    "PaymentSchema",
    "PaymentListSchema",
    "PaymentQuerySchema",
    "PaymentCreateSchema",
    "BankAccountSchema",
    "BankAccountDetailSchema",
    "BankAccountMovementSchema",
    "BankAccountListSchema",
    "BankAccountCreateSchema",
    "KpisSchema",
    "ChartsSchema",
    "ConsumptionSchema",
    "AccountBalanceSchema",
    "DashboardSchema",
]
