"""Expense web routes — list, detail, create and lifecycle actions."""
from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from models.enums import EntityType, ExpenseStatus
from repositories.status_history_repository import StatusHistoryRepository
from services.expense_service import ExpenseService

expense_bp = Blueprint("expenses", __name__, url_prefix="/expenses")
expense_service = ExpenseService()
history_repo = StatusHistoryRepository()


@expense_bp.route("/")
@login_required
def list_expenses():
    status_arg = request.args.get("status")
    status = _parse_status(status_arg)
    expenses = expense_service.list_expenses(status=status)
    return render_template(
        "expenses/list.html",
        expenses=expenses,
        statuses=list(ExpenseStatus),
        active_status=status_arg or "",
    )


@expense_bp.route("/new", methods=["GET", "POST"])
@login_required
def create_expense():
    if request.method == "POST":
        expense_service.create_expense(
            description=request.form.get("description", ""),
            amount=request.form.get("amount", ""),
            created_by=current_user.id,
        )
        flash("Gasto creado correctamente.", "success")
        return redirect(url_for("expenses.list_expenses"))
    return render_template("expenses/form.html")


@expense_bp.route("/<int:expense_id>")
@login_required
def detail(expense_id: int):
    expense = expense_service.get_or_404(expense_id)
    history = history_repo.for_entity(EntityType.EXPENSE, expense_id)
    return render_template("expenses/detail.html", expense=expense, history=history)


@expense_bp.route("/<int:expense_id>/approve", methods=["POST"])
@login_required
def approve(expense_id: int):
    expense_service.approve_expense(expense_id, user_id=current_user.id)
    flash("Gasto aprobado.", "success")
    return redirect(url_for("expenses.detail", expense_id=expense_id))


@expense_bp.route("/<int:expense_id>/cancel", methods=["POST"])
@login_required
def cancel(expense_id: int):
    expense_service.cancel_expense(expense_id, user_id=current_user.id)
    flash("Gasto cancelado.", "info")
    return redirect(url_for("expenses.detail", expense_id=expense_id))


def _parse_status(value: str | None) -> ExpenseStatus | None:
    if not value:
        return None
    try:
        return ExpenseStatus(value)
    except ValueError:
        return None
