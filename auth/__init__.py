"""Authentication package.

Wires up Flask-Login: the shared ``login_manager`` plus the user loader and
the unauthorized handler. ``init_auth(app)`` is called from the application
factory.
"""
from __future__ import annotations

from flask import flash, redirect, request, url_for
from flask_login import LoginManager

login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Por favor inicia sesión para continuar."
login_manager.login_message_category = "warning"


@login_manager.user_loader
def load_user(user_id: str):
    """Reload the user object from the session-stored id."""
    from models.user import User
    from database.db import db

    return db.session.get(User, int(user_id))


@login_manager.unauthorized_handler
def handle_unauthorized():
    """Send API clients a 401 JSON body; redirect browsers to the login page."""
    if request.path.startswith("/api/"):
        from flask import jsonify

        return jsonify({"error": "Autenticación requerida."}), 401
    flash(login_manager.login_message, login_manager.login_message_category)
    return redirect(url_for("auth.login", next=request.path))


def init_auth(app) -> None:
    login_manager.init_app(app)


__all__ = ["login_manager", "init_auth"]
