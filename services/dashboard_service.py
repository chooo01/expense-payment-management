"""Dashboard service — read-only aggregation for KPIs and charts.

Keeps all reporting math in one place so both the HTML dashboard and the
``GET /api/dashboard`` endpoint share identical numbers.
"""
from __future__ import annotations

from models.enums import ExpenseStatus, PaymentStatus
from repositories.bank_account_repository import BankAccountRepository
from repositories.expense_repository import ExpenseRepository
from repositories.payment_repository import PaymentRepository


class DashboardService:
    def __init__(
        self,
        expense_repository: ExpenseRepository | None = None,
        payment_repository: PaymentRepository | None = None,
        bank_account_repository: BankAccountRepository | None = None,
    ) -> None:
        self.expenses = expense_repository or ExpenseRepository()
        self.payments = payment_repository or PaymentRepository()
        self.accounts = bank_account_repository or BankAccountRepository()

    def kpis(self) -> dict:
        """Headline numbers shown as cards on the dashboard."""
        total_balance = sum(
            (a.current_balance for a in self.accounts.get_active()), 0
        )
        return {
            "total_expenses": self.expenses.total_amount(),
            "total_paid": self.payments.total_amount(PaymentStatus.PAID),
            "pending_expenses": self.expenses.count(ExpenseStatus.PENDING),
            "pending_payments": self.payments.count(PaymentStatus.PENDING),
            "available_balance": float(total_balance),
        }

    def charts(self, months: int = 6) -> dict:
        """Series consumed by Chart.js on the dashboard."""
        return {
            "expenses_by_month": self.expenses.monthly_totals(months),
            "payments_by_month": self.payments.monthly_totals(months),
            "expenses_by_status": self.expenses.count_by_status(),
            "payments_by_status": self.payments.count_by_status(),
            "consumption_by_account": [
                {"account_id": rid, "account_name": name, "total": total}
                for rid, name, total in self.payments.consumption_by_account()
            ],
        }

    def bank_account_balances(self) -> list[dict]:
        return [
            {
                "id": a.id,
                "account_name": a.account_name,
                "bank_name": a.bank_name,
                "current_balance": float(a.current_balance),
            }
            for a in self.accounts.get_active()
        ]

    def full_summary(self) -> dict:
        """Everything the ``GET /api/dashboard`` endpoint returns."""
        return {
            "kpis": self.kpis(),
            "charts": self.charts(),
            "bank_accounts": self.bank_account_balances(),
        }
