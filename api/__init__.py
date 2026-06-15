"""REST API package.

``register_api(app)`` mounts every read-only JSON Blueprint under ``/api``.
All API endpoints require an authenticated session (Flask-Login); unauthorized
requests receive a 401 JSON body (see ``auth/__init__.py``).
"""
from .bank_account_api import bank_account_api
from .dashboard_api import dashboard_api
from .expense_api import expense_api
from .payment_api import payment_api


def register_api(app) -> None:
    app.register_blueprint(expense_api)
    app.register_blueprint(payment_api)
    app.register_blueprint(bank_account_api)
    app.register_blueprint(dashboard_api)


__all__ = ["register_api"]
