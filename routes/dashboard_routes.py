"""Dashboard route — executive KPIs and charts."""
from __future__ import annotations

from flask import Blueprint, render_template
from flask_login import login_required

from services.dashboard_service import DashboardService

dashboard_bp = Blueprint("dashboard", __name__)
dashboard_service = DashboardService()


@dashboard_bp.route("/")
@dashboard_bp.route("/dashboard")
@login_required
def index():
    # KPIs are rendered server-side; charts are fed from /api/dashboard via JS.
    return render_template("dashboard/index.html", kpis=dashboard_service.kpis())
