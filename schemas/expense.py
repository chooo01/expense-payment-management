"""Expense schemas (output, detail with payments, query params)."""
from __future__ import annotations

from flask_marshmallow import Schema
from marshmallow import fields, validate

from models.enums import ExpenseStatus

from .common import EnumField
from .payment import PaymentSchema

_EXPENSE_STATUSES = [s.value for s in ExpenseStatus]


class ExpenseSchema(Schema):
    """Serialized representation of an expense (reusable component)."""

    id = fields.Integer(metadata={"example": 1})
    folio = fields.String(metadata={"description": "Folio único del gasto.", "example": "EXP-2026-000001"})
    description = fields.String(metadata={"example": "Compra de equipos de cómputo"})
    amount = fields.Float(metadata={"description": "Monto total del gasto.", "example": 25000.00})
    paid_amount = fields.Method("get_paid", metadata={"description": "Suma de pagos no cancelados.", "example": 25000.00})
    remaining_amount = fields.Method("get_remaining", metadata={"description": "Saldo pendiente por pagar.", "example": 0.00})
    status = EnumField(
        validate=validate.OneOf(_EXPENSE_STATUSES),
        metadata={"description": "Estado del gasto.", "example": "PAID"},
    )
    status_label = fields.Method("get_status_label", metadata={"example": "Pagado"})
    created_by = fields.Integer(metadata={"description": "Id del usuario creador.", "example": 1})
    approved_by = fields.Integer(allow_none=True, metadata={"description": "Id del aprobador (si aplica).", "example": 1})
    created_at = fields.DateTime(metadata={"example": "2026-06-15T12:00:00+00:00"})
    updated_at = fields.DateTime(metadata={"example": "2026-06-15T13:00:00+00:00"})

    def get_paid(self, obj):
        return float(obj.paid_amount())

    def get_remaining(self, obj):
        return float(obj.remaining_amount())

    def get_status_label(self, obj):
        return obj.status.label


class ExpenseDetailSchema(ExpenseSchema):
    """Expense detail — extends the base with its nested payments."""

    payments = fields.List(fields.Nested(PaymentSchema))


class ExpenseListSchema(Schema):
    """Envelope for ``GET /api/expenses``."""

    count = fields.Integer(metadata={"description": "Número de elementos.", "example": 2})
    data = fields.List(fields.Nested(ExpenseSchema))


class ExpenseQuerySchema(Schema):
    """Query string params for ``GET /api/expenses``."""

    status = fields.String(
        required=False,
        validate=validate.OneOf(_EXPENSE_STATUSES),
        metadata={"description": "Filtra por estado del gasto.", "example": "APPROVED"},
    )


class ExpenseCreateSchema(Schema):
    """Request body for ``POST /api/expenses``."""

    description = fields.String(
        required=True,
        validate=validate.Length(min=1, max=500),
        metadata={"description": "Descripción del gasto.", "example": "Compra de equipos de cómputo"},
    )
    amount = fields.Float(
        required=True,
        validate=validate.Range(min=0.01),
        metadata={"description": "Monto del gasto (mayor que 0).", "example": 25000.00},
    )
