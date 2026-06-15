"""REST API — Payments (read + write, documented with APIFairy)."""
from __future__ import annotations

from apifairy import arguments, authenticate, body, other_responses, response
from flask import Blueprint

from api.security import token_auth
from models.enums import PaymentStatus
from schemas.common import ErrorSchema, ValidationErrorSchema
from schemas.payment import (
    PaymentCreateSchema,
    PaymentListSchema,
    PaymentQuerySchema,
    PaymentSchema,
)
from services.payment_service import PaymentService

payment_api = Blueprint("payment_api", __name__, url_prefix="/api/payments")
service = PaymentService()

_AUTH_ERR = ["Token inválido o ausente.", ErrorSchema]
_NOT_FOUND = ["Pago no encontrado.", ErrorSchema]
_RULE_ERR = ["Regla de negocio violada (estado/saldo).", ErrorSchema]
_VALIDATION = ["Datos de entrada inválidos.", ValidationErrorSchema]


# --- Reads ------------------------------------------------------------------
@payment_api.route("", methods=["GET"])
@authenticate(token_auth)
@arguments(PaymentQuerySchema)
@response(PaymentListSchema)
@other_responses({401: _AUTH_ERR})
def list_payments(query):
    """Listar pagos.

    Admite filtrar por `status` y/o por `expense_id`.
    """
    status = PaymentStatus(query["status"]) if query.get("status") else None
    payments = service.list_payments(status=status, expense_id=query.get("expense_id"))
    return {"count": len(payments), "data": payments}


@payment_api.route("/<int:payment_id>", methods=["GET"])
@authenticate(token_auth)
@response(PaymentSchema)
@other_responses({401: _AUTH_ERR, 404: _NOT_FOUND})
def get_payment(payment_id):
    """Obtener un pago por id."""
    return service.get_or_404(payment_id)


# --- Writes -----------------------------------------------------------------
@payment_api.route("", methods=["POST"])
@authenticate(token_auth)
@body(PaymentCreateSchema)
@response(PaymentSchema, status_code=201, description="Pago generado en estado PENDIENTE.")
@other_responses(
    {
        400: _VALIDATION,
        401: _AUTH_ERR,
        404: ["Gasto o cuenta bancaria no encontrados.", ErrorSchema],
        409: ["El gasto no está aprobado, ya está pagado o el monto excede el pendiente.", ErrorSchema],
    }
)
def generate_payment(data):
    """Generar pago desde un gasto APROBADO ("Generar Pago").

    Soporta pagos parciales; evita el sobrepago (la suma de pagos no cancelados
    no puede exceder el monto del gasto).
    """
    user = token_auth.current_user()
    return service.generate_payment(
        expense_id=data["expense_id"],
        bank_account_id=data["bank_account_id"],
        amount=data["amount"],
        user_id=user.id,
    )


@payment_api.route("/<int:payment_id>/approve", methods=["POST"])
@authenticate(token_auth)
@response(PaymentSchema, description="Pago aprobado.")
@other_responses({401: _AUTH_ERR, 404: _NOT_FOUND, 409: _RULE_ERR})
def approve_payment(payment_id):
    """Aprobar pago (PENDIENTE → APROBADO)."""
    user = token_auth.current_user()
    return service.approve_payment(payment_id, user_id=user.id)


@payment_api.route("/<int:payment_id>/pay", methods=["POST"])
@authenticate(token_auth)
@response(PaymentSchema, description="Pago ejecutado; saldo de la cuenta descontado.")
@other_responses(
    {
        401: _AUTH_ERR,
        404: _NOT_FOUND,
        409: ["El pago no está APROBADO o el monto excede el saldo de la cuenta.", ErrorSchema],
    }
)
def execute_payment(payment_id):
    """Marcar pago como PAGADO (APROBADO → PAGADO).

    Descuenta el saldo de la cuenta y registra el movimiento en el ledger.
    """
    user = token_auth.current_user()
    return service.execute_payment(payment_id, user_id=user.id)


@payment_api.route("/<int:payment_id>/cancel", methods=["POST"])
@authenticate(token_auth)
@response(PaymentSchema, description="Pago cancelado (si estaba PAGADO, se revierte el saldo).")
@other_responses({401: _AUTH_ERR, 404: _NOT_FOUND, 409: _RULE_ERR})
def cancel_payment(payment_id):
    """Cancelar pago. Si estaba PAGADO, reintegra el saldo y reabre el gasto."""
    user = token_auth.current_user()
    return service.cancel_payment(payment_id, user_id=user.id)
