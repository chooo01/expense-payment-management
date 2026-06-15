"""Domain exceptions.

Services raise these typed errors instead of returning ad-hoc tuples. The
web/API layers translate them into flash messages or JSON error responses with
the right HTTP status code (see ``middleware/error_handlers.py``). Each carries
an ``http_status`` so the mapping is centralized and consistent.
"""
from __future__ import annotations


class DomainError(Exception):
    """Base class for all business-rule violations."""

    http_status = 400

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(DomainError):
    """A requested entity does not exist (or is soft-deleted)."""

    http_status = 404


class ValidationError(DomainError):
    """Input failed validation (bad amount, missing field, ...)."""

    http_status = 422


class BusinessRuleError(DomainError):
    """A state transition or invariant was violated (e.g. illegal status)."""

    http_status = 409


class AuthenticationError(DomainError):
    """Invalid credentials or disabled account."""

    http_status = 401
