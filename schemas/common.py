"""Reusable schema building blocks.

Centralizing shared fields and schemas (errors, the enum serializer) keeps the
documented contract DRY: every endpoint references the *same* ``ErrorSchema``
and the same enum handling, so OpenAPI emits a single reusable component.
"""
from __future__ import annotations

from flask_marshmallow import Schema  # adds .jsonify(), required by APIFairy
from marshmallow import fields


class EnumField(fields.String):
    """Serialize a ``(str, Enum)`` member to its ``.value``.

    Declared as a ``String`` subclass so apispec documents it as a string (and
    picks up a ``OneOf`` validator as an OpenAPI ``enum``), while serialization
    emits the plain value (e.g. ``"APPROVED"``) instead of ``"Status.APPROVED"``.
    """

    def _serialize(self, value, attr, obj, **kwargs):
        if value is None:
            return None
        return getattr(value, "value", str(value))


class ErrorSchema(Schema):
    """Standard error envelope returned by every API error (4xx/5xx)."""

    error = fields.String(
        metadata={
            "description": "Mensaje de error legible para el cliente.",
            "example": "Gasto 999 no encontrado.",
        }
    )


class ValidationErrorSchema(Schema):
    """Body returned by APIFairy when request/query validation fails (400)."""

    messages = fields.Dict(
        metadata={
            "description": "Errores de validación agrupados por campo.",
            "example": {"query": {"status": ["Must be one of: PENDING, APPROVED, CANCELLED, PAID."]}},
        }
    )
