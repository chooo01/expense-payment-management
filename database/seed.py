"""Database seeding.

Creates the initial admin user (no public registration, per the spec) plus a
small, realistic dataset so the dashboard and lists are populated on first run.
Idempotent: running it twice will not duplicate the admin user.
"""
from __future__ import annotations

import logging
from decimal import Decimal

from database.db import db
from services.auth_service import AuthService
from services.bank_account_service import BankAccountService
from services.expense_service import ExpenseService
from services.payment_service import PaymentService

logger = logging.getLogger(__name__)


def run_seed(app) -> None:
    with app.app_context():
        db.create_all()

        auth = AuthService()
        username = app.config["SEED_ADMIN_USERNAME"]
        password = app.config["SEED_ADMIN_PASSWORD"]

        if auth.users.exists_username(username):
            logger.info("Seed: admin user %r already exists; skipping demo data.", username)
            return

        admin = auth.create_user(username, password, active=True)
        logger.info("Seed: created admin user %r", username)

        bank_service = BankAccountService()
        expense_service = ExpenseService()
        payment_service = PaymentService()

        # --- Bank accounts --------------------------------------------------
        nomina = bank_service.create_account(
            account_name="Cuenta Nómina",
            bank_name="Santander",
            account_number="1234567890",
            initial_balance=Decimal("250000.00"),
        )
        operativa = bank_service.create_account(
            account_name="Cuenta Operativa",
            bank_name="BBVA",
            account_number="9876543210",
            initial_balance=Decimal("100000.00"),
        )

        # --- Expenses + payments in various states --------------------------
        # 1) Fully paid expense (demonstrates execution + balance debit).
        e1 = expense_service.create_expense(
            description="Compra de equipos de cómputo",
            amount=Decimal("25000.00"),
            created_by=admin.id,
        )
        expense_service.approve_expense(e1.id, user_id=admin.id)
        p1 = payment_service.generate_payment(
            expense_id=e1.id,
            bank_account_id=operativa.id,
            amount=Decimal("25000.00"),
            user_id=admin.id,
        )
        payment_service.approve_payment(p1.id, user_id=admin.id)
        payment_service.execute_payment(p1.id, user_id=admin.id)

        # 2) Approved expense with a partial, executed payment.
        e2 = expense_service.create_expense(
            description="Servicios de consultoría Q2",
            amount=Decimal("40000.00"),
            created_by=admin.id,
        )
        expense_service.approve_expense(e2.id, user_id=admin.id)
        p2 = payment_service.generate_payment(
            expense_id=e2.id,
            bank_account_id=nomina.id,
            amount=Decimal("15000.00"),
            user_id=admin.id,
        )
        payment_service.approve_payment(p2.id, user_id=admin.id)
        payment_service.execute_payment(p2.id, user_id=admin.id)

        # 3) Approved expense with a pending payment (awaiting execution).
        e3 = expense_service.create_expense(
            description="Renovación de licencias de software",
            amount=Decimal("18000.00"),
            created_by=admin.id,
        )
        expense_service.approve_expense(e3.id, user_id=admin.id)
        payment_service.generate_payment(
            expense_id=e3.id,
            bank_account_id=operativa.id,
            amount=Decimal("18000.00"),
            user_id=admin.id,
        )

        # 4) Pending expense (no payment yet).
        expense_service.create_expense(
            description="Mobiliario para sala de juntas",
            amount=Decimal("12000.00"),
            created_by=admin.id,
        )

        # 5) Cancelled expense (terminal state demo).
        e5 = expense_service.create_expense(
            description="Evento cancelado",
            amount=Decimal("8000.00"),
            created_by=admin.id,
        )
        expense_service.cancel_expense(e5.id, user_id=admin.id)

        logger.info("Seed: demo data created (5 expenses, 2 accounts, 3 payments).")
