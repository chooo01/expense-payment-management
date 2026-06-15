"""Bank-account web routes — list, detail (with ledger) and create."""
from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from services.bank_account_service import BankAccountService

bank_bp = Blueprint("bank_accounts", __name__, url_prefix="/bank-accounts")
bank_service = BankAccountService()


@bank_bp.route("/")
@login_required
def list_accounts():
    return render_template(
        "bank_accounts/list.html", accounts=bank_service.list_accounts()
    )


@bank_bp.route("/new", methods=["GET", "POST"])
@login_required
def create_account():
    if request.method == "POST":
        bank_service.create_account(
            account_name=request.form.get("account_name", ""),
            bank_name=request.form.get("bank_name", ""),
            account_number=request.form.get("account_number", ""),
            initial_balance=request.form.get("initial_balance", "0"),
        )
        flash("Cuenta bancaria creada.", "success")
        return redirect(url_for("bank_accounts.list_accounts"))
    return render_template("bank_accounts/form.html")


@bank_bp.route("/<int:account_id>")
@login_required
def detail(account_id: int):
    account = bank_service.get_or_404(account_id)
    movements = bank_service.get_movements(account_id)
    return render_template(
        "bank_accounts/detail.html", account=account, movements=movements
    )
