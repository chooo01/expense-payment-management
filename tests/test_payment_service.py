"""Tests for payment generation, execution and bank-balance impact."""
from __future__ import annotations

from decimal import Decimal

import pytest

from models.enums import ExpenseStatus, PaymentStatus
from services.exceptions import BusinessRuleError


def _approved_expense(services, admin_user, amount="10000"):
    expense = services["expense"].create_expense(
        description="Gasto", amount=amount, created_by=admin_user.id
    )
    services["expense"].approve_expense(expense.id, user_id=admin_user.id)
    return expense


def test_payment_requires_approved_expense(services, admin_user, bank_account):
    expense = services["expense"].create_expense(
        description="Gasto", amount="5000", created_by=admin_user.id
    )  # still PENDING
    with pytest.raises(BusinessRuleError):
        services["payment"].generate_payment(
            expense_id=expense.id,
            bank_account_id=bank_account.id,
            amount="5000",
            user_id=admin_user.id,
        )


def test_cannot_overpay_expense(services, admin_user, bank_account):
    expense = _approved_expense(services, admin_user, amount="10000")
    with pytest.raises(BusinessRuleError):
        services["payment"].generate_payment(
            expense_id=expense.id,
            bank_account_id=bank_account.id,
            amount="10000.01",
            user_id=admin_user.id,
        )


def test_partial_payments_accumulate(services, admin_user, bank_account):
    expense = _approved_expense(services, admin_user, amount="10000")
    p1 = services["payment"].generate_payment(
        expense_id=expense.id, bank_account_id=bank_account.id,
        amount="6000", user_id=admin_user.id,
    )
    assert expense.remaining_amount() == Decimal("4000.00")
    # A second partial payment is allowed up to the remaining amount...
    services["payment"].generate_payment(
        expense_id=expense.id, bank_account_id=bank_account.id,
        amount="4000", user_id=admin_user.id,
    )
    assert expense.remaining_amount() == Decimal("0.00")
    # ...but no further payment can be generated (duplicate prevention).
    with pytest.raises(BusinessRuleError):
        services["payment"].generate_payment(
            expense_id=expense.id, bank_account_id=bank_account.id,
            amount="1", user_id=admin_user.id,
        )
    assert p1.status == PaymentStatus.PENDING


def test_execute_payment_debits_balance_and_settles_expense(
    services, admin_user, bank_account
):
    expense = _approved_expense(services, admin_user, amount="10000")
    payment = services["payment"].generate_payment(
        expense_id=expense.id, bank_account_id=bank_account.id,
        amount="10000", user_id=admin_user.id,
    )
    services["payment"].approve_payment(payment.id, user_id=admin_user.id)
    services["payment"].execute_payment(payment.id, user_id=admin_user.id)

    assert payment.status == PaymentStatus.PAID
    assert payment.payment_date is not None
    # Balance dropped by the paid amount.
    assert bank_account.current_balance == Decimal("90000.00")
    # Fully-paid expense is promoted to PAID.
    assert expense.status == ExpenseStatus.PAID
    # A ledger movement was recorded.
    movements = services["bank"].get_movements(bank_account.id)
    assert any(m.movement_type.value == "DEBIT" and m.amount == Decimal("10000.00")
               for m in movements)


def test_cannot_pay_more_than_balance(services, admin_user):
    # Account with a small balance.
    account = services["bank"].create_account(
        account_name="Chica", bank_name="B", account_number="999",
        initial_balance="100",
    )
    expense = _approved_expense(services, admin_user, amount="5000")
    payment = services["payment"].generate_payment(
        expense_id=expense.id, bank_account_id=account.id,
        amount="5000", user_id=admin_user.id,
    )
    services["payment"].approve_payment(payment.id, user_id=admin_user.id)
    with pytest.raises(BusinessRuleError):
        services["payment"].execute_payment(payment.id, user_id=admin_user.id)
    # Balance untouched after the failed execution.
    assert account.current_balance == Decimal("100.00")


def test_execute_requires_approved_payment(services, admin_user, bank_account):
    expense = _approved_expense(services, admin_user, amount="3000")
    payment = services["payment"].generate_payment(
        expense_id=expense.id, bank_account_id=bank_account.id,
        amount="3000", user_id=admin_user.id,
    )  # PENDING, not approved
    with pytest.raises(BusinessRuleError):
        services["payment"].execute_payment(payment.id, user_id=admin_user.id)


def test_cancel_paid_payment_reverses_balance_and_reopens_expense(
    services, admin_user, bank_account
):
    expense = _approved_expense(services, admin_user, amount="10000")
    payment = services["payment"].generate_payment(
        expense_id=expense.id, bank_account_id=bank_account.id,
        amount="10000", user_id=admin_user.id,
    )
    services["payment"].approve_payment(payment.id, user_id=admin_user.id)
    services["payment"].execute_payment(payment.id, user_id=admin_user.id)
    assert expense.status == ExpenseStatus.PAID

    services["payment"].cancel_payment(payment.id, user_id=admin_user.id)
    assert payment.status == PaymentStatus.CANCELLED
    # Money returned to the account.
    assert bank_account.current_balance == Decimal("100000.00")
    # Expense is no longer fully covered -> reopened to APPROVED.
    assert expense.status == ExpenseStatus.APPROVED
    assert expense.remaining_amount() == Decimal("10000.00")


def test_cannot_cancel_expense_with_active_payments(services, admin_user, bank_account):
    expense = _approved_expense(services, admin_user, amount="5000")
    services["payment"].generate_payment(
        expense_id=expense.id, bank_account_id=bank_account.id,
        amount="5000", user_id=admin_user.id,
    )
    with pytest.raises(BusinessRuleError):
        services["expense"].cancel_expense(expense.id, user_id=admin_user.id)
