"""Authentication schemas (token issuance)."""
from __future__ import annotations

from flask_marshmallow import Schema
from marshmallow import fields, validate


class LoginSchema(Schema):
    """Request body for ``POST /api/tokens`` — exchanges credentials for a token."""

    username = fields.String(
        required=True,
        validate=validate.Length(min=1),
        metadata={"description": "Nombre de usuario.", "example": "admin"},
    )
    password = fields.String(
        required=True,
        load_only=True,
        validate=validate.Length(min=1),
        metadata={"description": "Contraseña en texto plano (se valida con bcrypt).", "example": "Admin123*"},
    )


class TokenSchema(Schema):
    """Response body for ``POST /api/tokens``."""

    token = fields.String(
        metadata={
            "description": "Token Bearer. Envíalo en el header `Authorization: Bearer <token>`.",
            "example": "ImFkbWluIg.aXc8rQ.x7nQ...signed-token",
        }
    )
    token_type = fields.String(metadata={"description": "Esquema de autenticación.", "example": "Bearer"})
    expires_in = fields.Integer(
        metadata={"description": "Vigencia del token en segundos.", "example": 3600}
    )
