"""REST API — Expenses (read-only).

Endpoints
---------
GET /api/expenses
    Optional query param ``status`` (PENDING|APPROVED|CANCELLED|PAID).
    Returns a list of expenses.

GET /api/expenses/<id>
    Returns a single expense including its payments.

Example response (GET /api/expenses/1)::

    {
      "id": 1,
      "folio": "EXP-2026-000001",
      "description": "Compra de equipos de cómputo",
      "amount": 25000.00,
      "paid_amount": 10000.00,
      "remaining_amount": 15000.00,
      "status": "APPROVED",
      "status_label": "Aprobado",
      "created_by": 1,
      "approved_by": 1,
      "created_at": "2026-06-15T12:00:00+00:00",
      "updated_at": "2026-06-15T12:30:00+00:00",
      "payments": [ ... ]
    }
"""
from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_login import login_required

from models.enums import ExpenseStatus
from services.expense_service import ExpenseService

expense_api = Blueprint("expense_api", __name__, url_prefix="/api/expenses")
service = ExpenseService()


@expense_api.route("", methods=["GET"])
@expense_api.route("/", methods=["GET"])
@login_required
def list_expenses():
    status_arg = request.args.get("status")
    status = None
    if status_arg:
        try:
            status = ExpenseStatus(status_arg.upper())
        except ValueError:
            return jsonify({"error": f"Estado inválido: {status_arg}"}), 422

    expenses = service.list_expenses(status=status)
    return jsonify(
        {
            "count": len(expenses),
            "data": [e.to_dict() for e in expenses],
        }
    )


@expense_api.route("/<int:expense_id>", methods=["GET"])
@login_required
def get_expense(expense_id: int):
    expense = service.get_or_404(expense_id)
    return jsonify(expense.to_dict(include_payments=True))
