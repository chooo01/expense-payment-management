"""REST API — Authentication (token issuance).

``POST /api/tokens`` is the only write endpoint and the only public one: it
exchanges credentials (``@body``) for a short-lived Bearer token used by every
other endpoint's ``@authenticate(token_auth)``.
"""
from __future__ import annotations

from apifairy import body, other_responses, response
from flask import Blueprint

from schemas.auth import LoginSchema, TokenSchema
from schemas.common import ErrorSchema, ValidationErrorSchema
from services.auth_service import AuthService
from services.token_service import DEFAULT_EXPIRES_IN, TokenService

token_api = Blueprint("token_api", __name__, url_prefix="/api/tokens")
auth_service = AuthService()
token_service = TokenService()


@token_api.route("", methods=["POST"])
@body(LoginSchema)
@response(TokenSchema, status_code=200, description="Token emitido correctamente.")
@other_responses(
    {
        400: ["Cuerpo de la petición inválido (validación).", ValidationErrorSchema],
        401: ["Credenciales inválidas o cuenta deshabilitada.", ErrorSchema],
    }
)
def create_token(credentials):
    """Autenticación — emite un token Bearer.

    Intercambia usuario y contraseña por un token de acceso de vida corta
    (1 hora). Usa el token en el resto de endpoints mediante el header
    `Authorization: Bearer <token>`. Las contraseñas se verifican con bcrypt;
    no se almacena ningún token en base de datos (es stateless y firmado).
    """
    user = auth_service.authenticate(credentials["username"], credentials["password"])
    return {
        "token": token_service.generate(user.id),
        "token_type": "Bearer",
        "expires_in": DEFAULT_EXPIRES_IN,
    }
