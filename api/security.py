"""API authentication scheme (Bearer token).

Defines the single ``token_auth`` object consumed by APIFairy's
``@authenticate`` decorator. Keeping it here (separate from the web's
Flask-Login session auth) lets the REST API use a stateless, header-based
scheme that documents cleanly in OpenAPI and is usable from Swagger UI.
"""
from __future__ import annotations

import logging

from flask_httpauth import HTTPTokenAuth

from repositories.user_repository import UserRepository
from services.token_service import TokenService

logger = logging.getLogger(__name__)

# scheme='Bearer' -> documented as `Authorization: Bearer <token>` in OpenAPI.
token_auth = HTTPTokenAuth(scheme="Bearer")


@token_auth.verify_token
def verify_token(token: str):
    """Resolve a Bearer token to the owning, active user (or ``None``)."""
    user_id = TokenService().verify(token)
    if user_id is None:
        return None
    user = UserRepository().get_by_id(user_id)
    if user is None or not user.active:
        return None
    return user


@token_auth.error_handler
def auth_error(status_code: int = 401):
    """Return the standard JSON error envelope for auth failures."""
    return {"error": "Token de autenticación inválido o ausente."}, status_code
