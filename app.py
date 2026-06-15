"""Application factory and CLI entry point.

The factory pattern (``create_app``) keeps the app configurable and testable:
tests build an isolated app with the testing config, while production/dev use
the env-driven config. Extensions are created elsewhere (unbound) and wired up
here, which avoids circular imports.

CLI commands:
    flask init-db   -> create all tables (dev convenience; use migrations in prod)
    flask seed      -> create the admin user + demo data
"""
from __future__ import annotations

import click
from flask import Flask, jsonify

from api import register_api
from auth import init_auth
from config import get_config
from database.db import db, migrate
from middleware import (
    configure_logging,
    register_error_handlers,
    register_request_logging,
)
from routes import register_routes
from services.auth_service import bcrypt


def create_app(config_object=None) -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(config_object or get_config())

    # Ensure the parent folder of a local SQLite file exists (dev fallback).
    _ensure_sqlite_dir(app)

    # --- Logging (before anything that might log) ---------------------------
    configure_logging(app)

    # --- Extensions ---------------------------------------------------------
    db.init_app(app)
    migrate.init_app(app, db)
    bcrypt.init_app(app)
    init_auth(app)

    # Import models so they register on the metadata for create_all/migrations.
    with app.app_context():
        import models  # noqa: F401

    # --- Blueprints ---------------------------------------------------------
    register_routes(app)   # server-rendered pages
    register_api(app)      # JSON REST API

    # --- Cross-cutting ------------------------------------------------------
    register_request_logging(app)
    register_error_handlers(app)

    # --- Template helpers ---------------------------------------------------
    @app.context_processor
    def inject_globals():
        from datetime import datetime

        return {"now": datetime.utcnow()}

    # --- Health check (useful for Render) -----------------------------------
    @app.route("/healthz")
    def healthz():
        return jsonify({"status": "ok"})

    # --- CLI ----------------------------------------------------------------
    _register_cli(app)

    return app


def _ensure_sqlite_dir(app: Flask) -> None:
    """Create the directory for a local SQLite database file if missing."""
    uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
    prefix = "sqlite:///"
    if uri.startswith(prefix) and ":memory:" not in uri:
        import os

        db_path = uri[len(prefix):]
        directory = os.path.dirname(db_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)


def _register_cli(app: Flask) -> None:
    @app.cli.command("init-db")
    def init_db():
        """Create all database tables (development convenience)."""
        db.create_all()
        click.echo("Database tables created.")

    @app.cli.command("seed")
    def seed():
        """Seed the database with an admin user and demo data."""
        from database.seed import run_seed

        run_seed(app)
        click.echo("Seed completed.")


# WSGI / `flask run` entry object.
app = create_app()


if __name__ == "__main__":
    # Local dev server. In production, gunicorn imports ``wsgi:app``.
    app.run(host="0.0.0.0", port=5000, debug=app.config.get("DEBUG", False))
