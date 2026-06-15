"""Database package.

Centralizes the single SQLAlchemy extension instance (``db``) and the
Flask-Migrate instance (``migrate``) so every layer imports them from one
place, avoiding circular imports between models and the application factory.
"""
from .db import db, migrate

__all__ = ["db", "migrate"]
