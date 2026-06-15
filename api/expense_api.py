"""REST API — Expenses (read + write, documented with APIFairy)."""
from __future__ import annotations

from apifairy import arguments, authenticate, body, other_responses, response
from flask import Blueprint

from api.security import token_auth
from models.enums import ExpenseStatus
from schemas.common import ErrorSchema, ValidationErrorSchema
from schemas.expense import (
    ExpenseCreateSchema,
    ExpenseDetailSchema,
    ExpenseListSchema,
    ExpenseQuerySchema,
    ExpenseSchema,
)
from services.expense_service import ExpenseService

expense_api = Blueprint("expense_api", __name__, url_prefix="/api/expenses")
service = ExpenseService()

# Reusable error documentation blocks.
_AUTH_ERR = ["Token inválido o ausente.", ErrorSchema]
_NOT_FOUND = ["Gasto no encontrado.", ErrorSchema]
_RULE_ERR = ["Transición de estado inválida (regla de negocio).", ErrorSchema]
_VALIDATION = ["Datos de entrada inválidos.", ValidationErrorSchema]


# --- Reads ------------------------------------------------------------------
@expense_api.route("", methods=["GET"])
@authenticate(token_auth)
@arguments(ExpenseQuerySchema)
@response(ExpenseListSchema)
@other_responses({401: _AUTH_ERR})
def list_expenses(query):
    """Listar gastos.

    Devuelve todos los gastos no eliminados, ordenados por fecha de creación
    (más recientes primero). Admite el filtro opcional `status`.
    """
    status = ExpenseStatus(query["status"]) if query.get("status") else None
    expenses = service.list_expenses(status=status)
    return {"count": len(expenses), "data": expenses}


@expense_api.route("/<int:expense_id>", methods=["GET"])
@authenticate(token_auth)
@response(ExpenseDetailSchema)
@other_responses({401: _AUTH_ERR, 404: _NOT_FOUND})
def get_expense(expense_id):
    """Obtener un gasto por id (incluye sus pagos)."""
    return service.get_or_404(expense_id)


# --- Writes -----------------------------------------------------------------
@expense_api.route("", methods=["POST"])
@authenticate(token_auth)
@body(ExpenseCreateSchema)
@response(ExpenseSchema, status_code=201, description="Gasto creado en estado PENDIENTE.")
@other_responses({400: _VALIDATION, 401: _AUTH_ERR, 422: ["Monto o descripción inválidos.", ErrorSchema]})
def create_expense(data):
    """Crear gasto.

    El gasto se crea en estado **PENDIENTE** a nombre del usuario autenticado.
    """
    user = token_auth.current_user()
    return service.create_expense(
        description=data["description"], amount=data["amount"], created_by=user.id
    )


@expense_api.route("/<int:expense_id>/approve", methods=["POST"])
@authenticate(token_auth)
@response(ExpenseSchema, description="Gasto aprobado.")
@other_responses({401: _AUTH_ERR, 404: _NOT_FOUND, 409: _RULE_ERR})
def approve_expense(expense_id):
    """Aprobar gasto (PENDIENTE → APROBADO)."""
    user = token_auth.current_user()
    return service.approve_expense(expense_id, user_id=user.id)


@expense_api.route("/<int:expense_id>/cancel", methods=["POST"])
@authenticate(token_auth)
@response(ExpenseSchema, description="Gasto cancelado.")
@other_responses({401: _AUTH_ERR, 404: _NOT_FOUND, 409: ["No cancelable (terminal o con pagos activos).", ErrorSchema]})
def cancel_expense(expense_id):
    """Cancelar gasto (PENDIENTE/APROBADO → CANCELADO; estado terminal)."""
    user = token_auth.current_user()
    return service.cancel_expense(expense_id, user_id=user.id)
