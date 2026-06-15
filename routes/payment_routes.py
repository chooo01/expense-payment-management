"""Payment web routes — generation from an expense and lifecycle actions."""
from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from models.enums import EntityType, PaymentStatus
from repositories.status_history_repository import StatusHistoryRepository
from services.bank_account_service import BankAccountService
from services.expense_service import ExpenseService
from services.payment_service import PaymentService

payment_bp = Blueprint("payments", __name__, url_prefix="/payments")
payment_service = PaymentService()
expense_service = ExpenseService()
bank_service = BankAccountService()
history_repo = StatusHistoryRepository()


@payment_bp.route("/")
@login_required
def list_payments():
    status_arg = request.args.get("status")
    status = _parse_status(status_arg)
    payments = payment_service.list_payments(status=status)
    return render_template(
        "payments/list.html",
        payments=payments,
        statuses=list(PaymentStatus),
        active_status=status_arg or "",
    )


@payment_bp.route("/generate/<int:expense_id>", methods=["GET", "POST"])
@login_required
def generate(expense_id: int):
    """The "Generar Pago" flow: pick an account + amount for an expense."""
    expense = expense_service.get_or_404(expense_id)
    if request.method == "POST":
        payment = payment_service.generate_payment(
            expense_id=expense_id,
            bank_account_id=int(request.form.get("bank_account_id", 0)),
            amount=request.form.get("amount", ""),
            user_id=current_user.id,
        )
        flash(f"Pago {payment.payment_folio} generado.", "success")
        return redirect(url_for("payments.detail", payment_id=payment.id))

    return render_template(
        "payments/generate.html",
        expense=expense,
        accounts=bank_service.list_accounts(only_active=True),
    )


@payment_bp.route("/<int:payment_id>")
@login_required
def detail(payment_id: int):
    payment = payment_service.get_or_404(payment_id)
    history = history_repo.for_entity(EntityType.PAYMENT, payment_id)
    return render_template("payments/detail.html", payment=payment, history=history)


@payment_bp.route("/<int:payment_id>/approve", methods=["POST"])
@login_required
def approve(payment_id: int):
    payment_service.approve_payment(payment_id, user_id=current_user.id)
    flash("Pago aprobado.", "success")
    return redirect(url_for("payments.detail", payment_id=payment_id))


@payment_bp.route("/<int:payment_id>/pay", methods=["POST"])
@login_required
def execute(payment_id: int):
    payment_service.execute_payment(payment_id, user_id=current_user.id)
    flash("Pago ejecutado. Saldo de la cuenta actualizado.", "success")
    return redirect(url_for("payments.detail", payment_id=payment_id))


@payment_bp.route("/<int:payment_id>/cancel", methods=["POST"])
@login_required
def cancel(payment_id: int):
    payment_service.cancel_payment(payment_id, user_id=current_user.id)
    flash("Pago cancelado.", "info")
    return redirect(url_for("payments.detail", payment_id=payment_id))


def _parse_status(value: str | None) -> PaymentStatus | None:
    if not value:
        return None
    try:
        return PaymentStatus(value)
    except ValueError:
        return None
