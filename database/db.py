"""SQLAlchemy / Flask-Migrate singletons.

These objects are created *unbound* here and attached to the Flask app inside
the application factory (``app.py``) via ``db.init_app(app)``. Keeping them in
their own module is the canonical way to avoid circular imports: models import
``db`` from here, and the factory imports both the models and ``db``.
"""
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

# The shared ORM handle. Models subclass ``db.Model``.
db = SQLAlchemy()

# Alembic-based migration engine, wired up in the application factory.
migrate = Migrate()
