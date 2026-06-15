"""Payment schemas (output + query params)."""
from __future__ import annotations

from flask_marshmallow import Schema
from marshmallow import fields, validate

from models.enums import PaymentStatus

from .common import EnumField

_PAYMENT_STATUSES = [s.value for s in PaymentStatus]


class PaymentSchema(Schema):
    """Serialized representation of a payment (reusable component)."""

    id = fields.Integer(metadata={"example": 1})
    payment_folio = fields.String(metadata={"description": "Folio único del pago.", "example": "PAY-2026-000001"})
    expense_id = fields.Integer(metadata={"example": 1})
    expense_folio = fields.Method("get_expense_folio", metadata={"description": "Folio del gasto origen.", "example": "EXP-2026-000001"})
    bank_account_id = fields.Integer(metadata={"example": 2})
    bank_account_name = fields.Method("get_account_name", metadata={"example": "Cuenta Operativa"})
    amount = fields.Float(metadata={"description": "Monto del pago.", "example": 25000.00})
    status = EnumField(
        validate=validate.OneOf(_PAYMENT_STATUSES),
        metadata={"description": "Estado del pago.", "example": "PAID"},
    )
    status_label = fields.Method("get_status_label", metadata={"example": "Pagado"})
    payment_date = fields.DateTime(allow_none=True, metadata={"description": "Fecha de ejecución (cuando pasa a PAGADO).", "example": "2026-06-15T13:00:00+00:00"})
    created_at = fields.DateTime(metadata={"example": "2026-06-15T12:45:00+00:00"})

    def get_expense_folio(self, obj):
        return obj.expense.folio if obj.expense else None

    def get_account_name(self, obj):
        return obj.bank_account.account_name if obj.bank_account else None

    def get_status_label(self, obj):
        return obj.status.label


class PaymentListSchema(Schema):
    """Envelope for ``GET /api/payments``."""

    count = fields.Integer(metadata={"description": "Número de elementos.", "example": 3})
    data = fields.List(fields.Nested(PaymentSchema))


class PaymentQuerySchema(Schema):
    """Query string params for ``GET /api/payments``."""

    status = fields.String(
        required=False,
        validate=validate.OneOf(_PAYMENT_STATUSES),
        metadata={"description": "Filtra por estado del pago.", "example": "PAID"},
    )
    expense_id = fields.Integer(
        required=False,
        metadata={"description": "Filtra los pagos de un gasto concreto.", "example": 1},
    )


class PaymentCreateSchema(Schema):
    """Request body for ``POST /api/payments`` (botón "Generar Pago")."""

    expense_id = fields.Integer(
        required=True,
        metadata={"description": "Id del gasto APROBADO de origen.", "example": 1},
    )
    bank_account_id = fields.Integer(
        required=True,
        metadata={"description": "Id de la cuenta bancaria que fondea el pago.", "example": 2},
    )
    amount = fields.Float(
        required=True,
        validate=validate.Range(min=0.01),
        metadata={"description": "Monto a pagar (admite pagos parciales).", "example": 25000.00},
    )
