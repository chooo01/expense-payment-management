"""Dashboard route — executive KPIs and charts."""
from __future__ import annotations

from flask import Blueprint, render_template
from flask_login import current_user, login_required

from services.dashboard_service import DashboardService
from services.token_service import TokenService

dashboard_bp = Blueprint("dashboard", __name__)
dashboard_service = DashboardService()
token_service = TokenService()


@dashboard_bp.route("/")
@dashboard_bp.route("/dashboard")
@login_required
def index():
    # KPIs are rendered server-side; charts are fed from the token-protected
    # /api/dashboard endpoint via JS. We mint a short-lived API token for the
    # logged-in user so the browser can call the API (single source of truth).
    return render_template(
        "dashboard/index.html",
        kpis=dashboard_service.kpis(),
        api_token=token_service.generate(current_user.id),
    )
