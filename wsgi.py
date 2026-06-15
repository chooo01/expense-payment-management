"""WSGI entry point for production servers (gunicorn).

    gunicorn wsgi:app

On first boot we ensure the schema exists. In a mature deployment you would
run ``flask db upgrade`` (Alembic migrations) instead; ``create_all`` is a safe
idempotent fallback so the demo deploys cleanly on Render.
"""
from app import app, create_app  # noqa: F401
from database.db import db


def _ensure_schema() -> None:
    with app.app_context():
        db.create_all()


_ensure_schema()

if __name__ == "__main__":
    app.run()
