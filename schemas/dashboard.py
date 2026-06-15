"""Dashboard summary schema (KPIs + chart series)."""
from __future__ import annotations

from flask_marshmallow import Schema
from marshmallow import fields


class KpisSchema(Schema):
    """Headline indicators for the executive dashboard."""

    total_expenses = fields.Float(metadata={"description": "Suma de todos los gastos.", "example": 103000.00})
    total_paid = fields.Float(metadata={"description": "Suma de pagos ejecutados (PAGADO).", "example": 40000.00})
    pending_expenses = fields.Integer(metadata={"description": "Gastos en estado PENDIENTE.", "example": 1})
    pending_payments = fields.Integer(metadata={"description": "Pagos en estado PENDIENTE.", "example": 1})
    available_balance = fields.Float(metadata={"description": "Saldo agregado de cuentas activas.", "example": 310000.00})


class ConsumptionSchema(Schema):
    """Executed amount grouped by bank account."""

    account_id = fields.Integer(metadata={"example": 2})
    account_name = fields.String(metadata={"example": "Cuenta Operativa"})
    total = fields.Float(metadata={"example": 25000.00})


class AccountBalanceSchema(Schema):
    """Per-account available balance shown on the dashboard."""

    id = fields.Integer(metadata={"example": 1})
    account_name = fields.String(metadata={"example": "Cuenta Nómina"})
    bank_name = fields.String(metadata={"example": "Santander"})
    current_balance = fields.Float(metadata={"example": 235000.00})


class ChartsSchema(Schema):
    """Series consumed by the Chart.js widgets."""

    expenses_by_month = fields.List(
        fields.Tuple([fields.String(), fields.Float()]),
        metadata={"description": "Pares [YYYY-MM, monto].", "example": [["2026-05", 0.0], ["2026-06", 103000.0]]},
    )
    payments_by_month = fields.List(
        fields.Tuple([fields.String(), fields.Float()]),
        metadata={"description": "Pares [YYYY-MM, monto].", "example": [["2026-05", 0.0], ["2026-06", 40000.0]]},
    )
    expenses_by_status = fields.Dict(
        keys=fields.String(), values=fields.Integer(),
        metadata={"description": "Conteo de gastos por estado.", "example": {"PENDING": 1, "APPROVED": 2, "PAID": 1, "CANCELLED": 1}},
    )
    payments_by_status = fields.Dict(
        keys=fields.String(), values=fields.Integer(),
        metadata={"description": "Conteo de pagos por estado.", "example": {"PENDING": 1, "PAID": 2}},
    )
    consumption_by_account = fields.List(fields.Nested(ConsumptionSchema))


class DashboardSchema(Schema):
    """Full payload of ``GET /api/dashboard``."""

    kpis = fields.Nested(KpisSchema)
    charts = fields.Nested(ChartsSchema)
    bank_accounts = fields.List(fields.Nested(AccountBalanceSchema))
