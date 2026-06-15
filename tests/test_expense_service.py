"""Tests for the expense state machine and validations."""
from __future__ import annotations

from decimal import Decimal

import pytest

from models.enums import ExpenseStatus
from services.exceptions import BusinessRuleError, ValidationError


def _create(services, admin_user, amount="1000"):
    return services["expense"].create_expense(
        description="Test", amount=amount, created_by=admin_user.id
    )


def test_expense_starts_pending(services, admin_user):
    expense = _create(services, admin_user)
    assert expense.status == ExpenseStatus.PENDING
    assert expense.folio.startswith("EXP-")


def test_amount_must_be_positive(services, admin_user):
    with pytest.raises(ValidationError):
        _create(services, admin_user, amount="0")
    with pytest.raises(ValidationError):
        _create(services, admin_user, amount="-5")
    with pytest.raises(ValidationError):
        _create(services, admin_user, amount="abc")


def test_description_required(services, admin_user):
    with pytest.raises(ValidationError):
        services["expense"].create_expense(
            description="   ", amount="100", created_by=admin_user.id
        )


def test_approve_then_cannot_reapprove(services, admin_user):
    expense = _create(services, admin_user)
    services["expense"].approve_expense(expense.id, user_id=admin_user.id)
    assert expense.status == ExpenseStatus.APPROVED
    assert expense.approved_by == admin_user.id
    # PENDING is the only state that can be approved.
    with pytest.raises(BusinessRuleError):
        services["expense"].approve_expense(expense.id, user_id=admin_user.id)


def test_cancelled_is_terminal(services, admin_user):
    expense = _create(services, admin_user)
    services["expense"].cancel_expense(expense.id, user_id=admin_user.id)
    assert expense.status == ExpenseStatus.CANCELLED
    # Cannot reactivate (approve) a cancelled expense.
    with pytest.raises(BusinessRuleError):
        services["expense"].approve_expense(expense.id, user_id=admin_user.id)


def test_folio_is_sequential(services, admin_user):
    e1 = _create(services, admin_user)
    e2 = _create(services, admin_user)
    assert e1.folio != e2.folio
    assert int(e2.folio.split("-")[-1]) == int(e1.folio.split("-")[-1]) + 1
