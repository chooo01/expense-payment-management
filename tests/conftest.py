"""Pytest fixtures.

Builds an isolated app with the in-memory testing config, creates the schema
once per test, and provides ready-to-use services plus an authenticated test
client. Each test gets a fresh database (function scope) for full isolation.
"""
from __future__ import annotations

import os
import sys
from decimal import Decimal

import pytest

# Make the project importable when running `pytest` from the repo root.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app  # noqa: E402
from config import TestingConfig  # noqa: E402
from database.db import db  # noqa: E402
from services.auth_service import AuthService  # noqa: E402
from services.bank_account_service import BankAccountService  # noqa: E402
from services.expense_service import ExpenseService  # noqa: E402
from services.payment_service import PaymentService  # noqa: E402


@pytest.fixture()
def app():
    app = create_app(TestingConfig())
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def admin_user(app):
    return AuthService().create_user("admin", "Admin123*")


@pytest.fixture()
def auth_client(app, admin_user):
    """A test client with an active logged-in session."""
    c = app.test_client()
    c.post("/login", data={"username": "admin", "password": "Admin123*"})
    return c


@pytest.fixture()
def services():
    return {
        "expense": ExpenseService(),
        "payment": PaymentService(),
        "bank": BankAccountService(),
    }


@pytest.fixture()
def bank_account(app):
    return BankAccountService().create_account(
        account_name="Cuenta Test",
        bank_name="Banco Test",
        account_number="0001112223",
        initial_balance=Decimal("100000.00"),
    )
