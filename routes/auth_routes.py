"""Authentication routes — login / logout (session based)."""
from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from urllib.parse import urlparse

from services.auth_service import AuthService
from services.exceptions import DomainError

auth_bp = Blueprint("auth", __name__)
auth_service = AuthService()


def _is_safe_next(target: str | None) -> bool:
    """Only allow local redirects to avoid open-redirect attacks."""
    if not target:
        return False
    parsed = urlparse(target)
    return not parsed.netloc and not parsed.scheme and target.startswith("/")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        try:
            user = auth_service.authenticate(username, password)
        except DomainError as exc:
            flash(exc.message, "danger")
            return render_template("auth/login.html", username=username), exc.http_status

        login_user(user)
        flash(f"Bienvenido, {user.username}.", "success")
        next_url = request.args.get("next")
        return redirect(next_url if _is_safe_next(next_url) else url_for("dashboard.index"))

    return render_template("auth/login.html")


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("Sesión cerrada correctamente.", "info")
    return redirect(url_for("auth.login"))
