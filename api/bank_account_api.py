"""REST API — Bank accounts (read-only).

Endpoints
---------
GET /api/bank-accounts
GET /api/bank-accounts/<id>   (includes recent movements)

Example response (GET /api/bank-accounts/2)::

    {
      "id": 2,
      "account_name": "Cuenta Operativa",
      "bank_name": "BBVA",
      "account_number": "********4321",
      "current_balance": 90000.00,
      "active": true,
      "movements": [
        {
          "id": 5,
          "movement_type": "DEBIT",
          "amount": 10000.00,
          "balance_after": 90000.00,
          "description": "Pago PAY-2026-000001 (gasto EXP-2026-000001)",
          "created_at": "2026-06-15T13:00:00+00:00"
        }
      ]
    }
"""
from __future__ import annotations

from flask import Blueprint, jsonify
from flask_login import login_required

from services.bank_account_service import BankAccountService

bank_account_api = Blueprint(
    "bank_account_api", __name__, url_prefix="/api/bank-accounts"
)
service = BankAccountService()


@bank_account_api.route("", methods=["GET"])
@bank_account_api.route("/", methods=["GET"])
@login_required
def list_accounts():
    accounts = service.list_accounts()
    return jsonify(
        {
            "count": len(accounts),
            "data": [a.to_dict() for a in accounts],
        }
    )


@bank_account_api.route("/<int:account_id>", methods=["GET"])
@login_required
def get_account(account_id: int):
    account = service.get_or_404(account_id)
    data = account.to_dict()
    data["movements"] = [m.to_dict() for m in service.get_movements(account_id)]
    return jsonify(data)
