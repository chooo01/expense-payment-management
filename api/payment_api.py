"""REST API — Payments (read-only).

Endpoints
---------
GET /api/payments
    Optional query params ``status`` and ``expense_id``.
GET /api/payments/<id>

Example response (GET /api/payments/1)::

    {
      "id": 1,
      "payment_folio": "PAY-2026-000001",
      "expense_id": 1,
      "expense_folio": "EXP-2026-000001",
      "bank_account_id": 2,
      "bank_account_name": "Cuenta Operativa",
      "amount": 10000.00,
      "status": "PAID",
      "status_label": "Pagado",
      "payment_date": "2026-06-15T13:00:00+00:00",
      "created_at": "2026-06-15T12:45:00+00:00"
    }
"""
from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_login import login_required

from models.enums import PaymentStatus
from services.payment_service import PaymentService

payment_api = Blueprint("payment_api", __name__, url_prefix="/api/payments")
service = PaymentService()


@payment_api.route("", methods=["GET"])
@payment_api.route("/", methods=["GET"])
@login_required
def list_payments():
    status = None
    status_arg = request.args.get("status")
    if status_arg:
        try:
            status = PaymentStatus(status_arg.upper())
        except ValueError:
            return jsonify({"error": f"Estado inválido: {status_arg}"}), 422

    expense_id = request.args.get("expense_id", type=int)
    payments = service.list_payments(status=status, expense_id=expense_id)
    return jsonify(
        {
            "count": len(payments),
            "data": [p.to_dict() for p in payments],
        }
    )


@payment_api.route("/<int:payment_id>", methods=["GET"])
@login_required
def get_payment(payment_id: int):
    payment = service.get_or_404(payment_id)
    return jsonify(payment.to_dict())
