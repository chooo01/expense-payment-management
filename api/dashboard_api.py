"""REST API — Dashboard summary (read-only).

Endpoint
--------
GET /api/dashboard

Returns headline KPIs, chart series and per-account balances. This single
endpoint feeds the Chart.js widgets on the dashboard page.

Example response::

    {
      "kpis": {
        "total_expenses": 125000.00,
        "total_paid": 80000.00,
        "pending_expenses": 3,
        "pending_payments": 2,
        "available_balance": 420000.00
      },
      "charts": {
        "expenses_by_month": [["2026-01", 10000.0], ["2026-02", 22000.0]],
        "payments_by_month": [["2026-01", 8000.0],  ["2026-02", 15000.0]],
        "expenses_by_status": {"PENDING": 3, "APPROVED": 5, "PAID": 4, "CANCELLED": 1},
        "payments_by_status": {"PENDING": 2, "APPROVED": 1, "PAID": 6, "CANCELLED": 1},
        "consumption_by_account": [
          {"account_id": 1, "account_name": "Cuenta Nómina", "total": 40000.0}
        ]
      },
      "bank_accounts": [
        {"id": 1, "account_name": "Cuenta Nómina", "bank_name": "Santander",
         "current_balance": 220000.0}
      ]
    }
"""
from __future__ import annotations

from flask import Blueprint, jsonify
from flask_login import login_required

from services.dashboard_service import DashboardService

dashboard_api = Blueprint("dashboard_api", __name__, url_prefix="/api/dashboard")
service = DashboardService()


@dashboard_api.route("", methods=["GET"])
@dashboard_api.route("/", methods=["GET"])
@login_required
def get_dashboard():
    return jsonify(service.full_summary())
