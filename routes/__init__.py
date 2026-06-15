"""Web routes package.

``register_routes(app)`` mounts every server-rendered Blueprint. The REST API
Blueprints live separately under ``api/`` and are registered by the factory
too.
"""
from .auth_routes import auth_bp
from .bank_account_routes import bank_bp
from .dashboard_routes import dashboard_bp
from .expense_routes import expense_bp
from .payment_routes import payment_bp


def register_routes(app) -> None:
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(expense_bp)
    app.register_blueprint(payment_bp)
    app.register_blueprint(bank_bp)


__all__ = ["register_routes"]
