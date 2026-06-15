"""Authentication service — credential checks and user provisioning.

Passwords are hashed with bcrypt (via Flask-Bcrypt). The plaintext password
never leaves this layer and is never persisted.
"""
from __future__ import annotations

import logging

from flask_bcrypt import Bcrypt

from database.db import db
from models.user import User
from repositories.user_repository import UserRepository

from .exceptions import AuthenticationError, ValidationError

logger = logging.getLogger(__name__)

# Module-level Bcrypt; initialized lazily so it works with the app factory.
bcrypt = Bcrypt()


class AuthService:
    def __init__(self, user_repository: UserRepository | None = None) -> None:
        self.users = user_repository or UserRepository()

    # --- Credentials --------------------------------------------------------
    def authenticate(self, username: str, password: str) -> User:
        """Return the user when credentials are valid, else raise.

        Note: the same generic error is raised for unknown user, wrong
        password and disabled account to avoid leaking which usernames exist.
        """
        if not username or not password:
            raise ValidationError("Usuario y contraseña son obligatorios.")

        user = self.users.get_by_username(username.strip())
        if user is None or not bcrypt.check_password_hash(user.password_hash, password):
            logger.warning("Failed login attempt for username=%r", username)
            raise AuthenticationError("Credenciales inválidas.")

        if not user.active:
            logger.warning("Login attempt on disabled account username=%r", username)
            raise AuthenticationError("La cuenta está deshabilitada.")

        logger.info("User %r authenticated", username)
        return user

    # --- Provisioning -------------------------------------------------------
    def create_user(self, username: str, password: str, *, active: bool = True) -> User:
        """Create a user with a bcrypt-hashed password (used by the seeder)."""
        username = (username or "").strip()
        if not username or not password:
            raise ValidationError("Usuario y contraseña son obligatorios.")
        if len(password) < 6:
            raise ValidationError("La contraseña debe tener al menos 6 caracteres.")
        if self.users.exists_username(username):
            raise ValidationError(f"El usuario '{username}' ya existe.")

        user = User(
            username=username,
            password_hash=bcrypt.generate_password_hash(password).decode("utf-8"),
            active=active,
        )
        self.users.add(user)
        db.session.commit()
        logger.info("Created user %r", username)
        return user
