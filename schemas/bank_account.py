"""Bank-account schemas (output, detail with movements)."""
from __future__ import annotations

from flask_marshmallow import Schema
from marshmallow import fields, validate

from models.enums import MovementType

from .common import EnumField


class BankAccountSchema(Schema):
    """Serialized bank account (account number is masked, reusable component)."""

    id = fields.Integer(metadata={"example": 2})
    account_name = fields.String(metadata={"example": "Cuenta Operativa"})
    bank_name = fields.String(metadata={"example": "BBVA"})
    account_number = fields.Method("get_masked_number", metadata={"description": "Número enmascarado (solo últimos 4 dígitos).", "example": "******3210"})
    current_balance = fields.Float(metadata={"description": "Saldo disponible.", "example": 75000.00})
    active = fields.Boolean(metadata={"example": True})

    def get_masked_number(self, obj):
        return obj._masked_number()


class BankAccountMovementSchema(Schema):
    """A single ledger entry (immutable record of a balance change)."""

    id = fields.Integer(metadata={"example": 1})
    bank_account_id = fields.Integer(metadata={"example": 2})
    payment_id = fields.Integer(allow_none=True, metadata={"example": 1})
    movement_type = EnumField(
        validate=validate.OneOf([m.value for m in MovementType]),
        metadata={"description": "DEBIT (salida) o CREDIT (entrada).", "example": "DEBIT"},
    )
    amount = fields.Float(metadata={"example": 25000.00})
    balance_after = fields.Float(metadata={"description": "Saldo resultante tras el movimiento.", "example": 75000.00})
    description = fields.String(allow_none=True, metadata={"example": "Pago PAY-2026-000001 (gasto EXP-2026-000001)"})
    created_at = fields.DateTime(metadata={"example": "2026-06-15T13:00:00+00:00"})


class BankAccountDetailSchema(BankAccountSchema):
    """Bank-account detail — extends the base with its movement ledger."""

    movements = fields.List(fields.Nested(BankAccountMovementSchema))


class BankAccountListSchema(Schema):
    """Envelope for ``GET /api/bank-accounts``."""

    count = fields.Integer(metadata={"description": "Número de elementos.", "example": 2})
    data = fields.List(fields.Nested(BankAccountSchema))


class BankAccountCreateSchema(Schema):
    """Request body for ``POST /api/bank-accounts``."""

    account_name = fields.String(required=True, validate=validate.Length(min=1), metadata={"example": "Cuenta Operativa"})
    bank_name = fields.String(required=True, validate=validate.Length(min=1), metadata={"example": "BBVA"})
    account_number = fields.String(required=True, validate=validate.Length(min=1), metadata={"description": "Número de cuenta (único).", "example": "9876543210"})
    initial_balance = fields.Float(
        load_default=0,
        validate=validate.Range(min=0),
        metadata={"description": "Saldo inicial (>= 0).", "example": 100000.00},
    )
