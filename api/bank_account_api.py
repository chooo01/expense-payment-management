"""REST API — Bank accounts (read + write, documented with APIFairy)."""
from __future__ import annotations

from apifairy import authenticate, body, other_responses, response
from flask import Blueprint

from api.security import token_auth
from schemas.bank_account import (
    BankAccountCreateSchema,
    BankAccountDetailSchema,
    BankAccountListSchema,
    BankAccountSchema,
)
from schemas.common import ErrorSchema, ValidationErrorSchema
from services.bank_account_service import BankAccountService

bank_account_api = Blueprint(
    "bank_account_api", __name__, url_prefix="/api/bank-accounts"
)
service = BankAccountService()

_AUTH_ERR = ["Token inválido o ausente.", ErrorSchema]
_NOT_FOUND = ["Cuenta bancaria no encontrada.", ErrorSchema]
_VALIDATION = ["Datos de entrada inválidos.", ValidationErrorSchema]


# --- Reads ------------------------------------------------------------------
@bank_account_api.route("", methods=["GET"])
@authenticate(token_auth)
@response(BankAccountListSchema)
@other_responses({401: _AUTH_ERR})
def list_accounts():
    """Listar cuentas bancarias (número enmascarado)."""
    accounts = service.list_accounts()
    return {"count": len(accounts), "data": accounts}


@bank_account_api.route("/<int:account_id>", methods=["GET"])
@authenticate(token_auth)
@response(BankAccountDetailSchema)
@other_responses({401: _AUTH_ERR, 404: _NOT_FOUND})
def get_account(account_id):
    """Obtener una cuenta por id (incluye su ledger de movimientos)."""
    return service.get_or_404(account_id)


# --- Writes -----------------------------------------------------------------
@bank_account_api.route("", methods=["POST"])
@authenticate(token_auth)
@body(BankAccountCreateSchema)
@response(BankAccountSchema, status_code=201, description="Cuenta bancaria creada.")
@other_responses({400: _VALIDATION, 401: _AUTH_ERR, 422: ["Datos inválidos o número duplicado.", ErrorSchema]})
def create_account(data):
    """Crear cuenta bancaria.

    Si el saldo inicial es mayor que 0, se registra un movimiento `CREDIT`
    inicial en el ledger.
    """
    return service.create_account(
        account_name=data["account_name"],
        bank_name=data["bank_name"],
        account_number=data["account_number"],
        initial_balance=data.get("initial_balance", 0),
    )
