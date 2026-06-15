"""Stateless API token service.

Issues and verifies signed Bearer tokens for the REST API using
``itsdangerous`` (ships with Flask) and the app ``SECRET_KEY``. Stateless means
no token table / migration is needed: the token itself carries the signed user
id and an embedded timestamp for expiry.

Why a separate service (SOLID / Single Responsibility): token creation and
verification are an isolated concern, decoupled from credential checking
(``AuthService``) and from the HTTP layer (``api/security.py``).
"""
from __future__ import annotations

from flask import current_app
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

# Default token lifetime (seconds).
DEFAULT_EXPIRES_IN = 3600


class TokenService:
    _SALT = "expensepay-api-token"

    def _serializer(self) -> URLSafeTimedSerializer:
        # Built per call so it always uses the current app's SECRET_KEY.
        return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt=self._SALT)

    def generate(self, user_id: int) -> str:
        """Return a signed token encoding ``user_id``."""
        return self._serializer().dumps({"uid": user_id})

    def verify(self, token: str, max_age: int = DEFAULT_EXPIRES_IN) -> int | None:
        """Return the ``user_id`` for a valid, unexpired token, else ``None``."""
        try:
            data = self._serializer().loads(token, max_age=max_age)
        except (BadSignature, SignatureExpired):
            return None
        return data.get("uid")
