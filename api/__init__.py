"""REST API package.

``register_api(app)`` mounts every JSON Blueprint under ``/api``. The read
endpoints are protected with a Bearer token (APIFairy ``@authenticate``); the
only public, write endpoint is ``POST /api/tokens`` (login → token).
OpenAPI/Swagger is served at ``/docs`` (see the application factory).
"""
from .auth_api import token_api
from .bank_account_api import bank_account_api
from .dashboard_api import dashboard_api
from .expense_api import expense_api
from .payment_api import payment_api


def register_api(app) -> None:
    app.register_blueprint(token_api)
    app.register_blueprint(expense_api)
    app.register_blueprint(payment_api)
    app.register_blueprint(bank_account_api)
    app.register_blueprint(dashboard_api)


__all__ = ["register_api"]
