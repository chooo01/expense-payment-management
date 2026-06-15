"""Application configuration classes.

Why a class hierarchy instead of a flat dict?
    - Each environment (development / testing / production) inherits sensible
      defaults from :class:`Config` and overrides only what differs.
    - Configuration is resolved once, at startup, and injected into the Flask
      app via ``app.config.from_object`` inside the application factory.

The active configuration is chosen with the ``FLASK_ENV`` environment
variable (development | testing | production).
"""
from __future__ import annotations

import os
from datetime import timedelta
from urllib.parse import urlsplit

# Load variables from a local .env file when present (no-op in production
# where the platform injects real environment variables).
from dotenv import load_dotenv

load_dotenv()

# Absolute path to the project root, used to anchor the SQLite fallback file.
BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

# Hosts that are treated as local Postgres (no SSL forced).
_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", ""}


def _ensure_sslmode(url: str) -> str:
    """Append ``sslmode`` for remote PostgreSQL (e.g. Render).

    Render's managed PostgreSQL requires TLS for external connections and
    supports it internally, so we default to ``sslmode=require`` for any
    non-local host. Local Postgres often ships without TLS, so we skip it for
    localhost. The behaviour can be overridden with the ``DB_SSLMODE`` env var
    (set it empty to disable), and an ``sslmode`` already present in the URL is
    always respected.
    """
    if "sslmode=" in url:
        return url

    override = os.getenv("DB_SSLMODE")
    if override is not None:
        sslmode = override.strip()
        if not sslmode:
            return url
    else:
        host = (urlsplit(url).hostname or "").lower()
        if host in _LOCAL_HOSTS:
            return url
        sslmode = "require"

    separator = "&" if "?" in url else "?"
    return f"{url}{separator}sslmode={sslmode}"


def _normalize_database_url(url: str | None) -> str | None:
    """Normalize the database URL for SQLAlchemy + Render.

    Render (and Heroku) hand out URLs that start with ``postgres://`` but
    SQLAlchemy 2.x requires the ``postgresql://`` scheme (and we pin the
    psycopg2 driver explicitly). This rewrites the scheme and, for remote
    PostgreSQL, ensures an ``sslmode`` so the same code works locally and on
    the platform without manual edits.
    """
    if not url:
        return None
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)

    if url.startswith("postgresql"):
        url = _ensure_sslmode(url)
    return url


def _build_engine_options(database_uri: str) -> dict:
    """SQLAlchemy engine options tuned per backend.

    PostgreSQL on Render's free tier has a low connection cap and drops idle
    connections after a few minutes, so we keep a small pool, pre-ping to
    transparently replace dead connections, and recycle before the idle
    timeout. SQLite (dev/tests) only gets ``pool_pre_ping`` — ``pool_size`` /
    ``max_overflow`` are QueuePool-only and break SQLite's pool implementation.
    """
    if database_uri.startswith("postgresql"):
        return {
            "pool_pre_ping": True,   # replace connections dropped by Render
            "pool_recycle": 280,     # recycle before Render's ~5 min idle drop
            "pool_size": 5,          # steady connections per gunicorn worker
            "max_overflow": 2,       # small burst headroom (free-tier safe)
            "pool_timeout": 30,
        }
    return {"pool_pre_ping": True}


class Config:
    """Base configuration shared by every environment."""

    # --- Security -----------------------------------------------------------
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-insecure-secret-key")

    # Session cookie hardening. Secure flag is enabled only in production
    # (HTTPS) so local HTTP development keeps working.
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = False
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)

    # --- Database -----------------------------------------------------------
    SQLALCHEMY_DATABASE_URI = _normalize_database_url(os.getenv("DATABASE_URL")) or (
        "sqlite:///" + os.path.join(BASE_DIR, "instance", "expenses.db")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Pooling tuned per backend (PostgreSQL/Render vs. SQLite).
    SQLALCHEMY_ENGINE_OPTIONS = _build_engine_options(SQLALCHEMY_DATABASE_URI)

    # --- Logging ------------------------------------------------------------
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

    # --- API documentation (APIFairy / OpenAPI) -----------------------------
    APIFAIRY_TITLE = "ExpensePay API"
    APIFAIRY_VERSION = "1.0.0"
    APIFAIRY_UI = "swagger_ui"          # Swagger UI served at /docs
    APIFAIRY_UI_PATH = "/docs"
    APIFAIRY_APISPEC_PATH = "/openapi.json"

    # --- Seed ---------------------------------------------------------------
    SEED_ADMIN_USERNAME = os.getenv("SEED_ADMIN_USERNAME", "admin")
    SEED_ADMIN_PASSWORD = os.getenv("SEED_ADMIN_PASSWORD", "Admin123*")

    TESTING = False
    DEBUG = False


class DevelopmentConfig(Config):
    """Local development: verbose, auto-reload friendly."""

    DEBUG = True
    LOG_LEVEL = "DEBUG"


class TestingConfig(Config):
    """Automated tests: in-memory DB, CSRF/secure cookies relaxed."""

    TESTING = True
    DEBUG = True
    # In-memory SQLite keeps the test suite fast and isolated.
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_ENGINE_OPTIONS = _build_engine_options(SQLALCHEMY_DATABASE_URI)
    WTF_CSRF_ENABLED = False
    SECRET_KEY = "testing-secret-key"


class ProductionConfig(Config):
    """Production: strict cookies, secret key must be provided externally."""

    SESSION_COOKIE_SECURE = True

    def __init__(self) -> None:
        # Fail fast if the operator forgot to set a real secret key.
        if self.SECRET_KEY == "dev-only-insecure-secret-key":
            raise RuntimeError(
                "SECRET_KEY must be set to a strong value in production."
            )


_CONFIG_BY_NAME: dict[str, type[Config]] = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def get_config(env: str | None = None) -> Config:
    """Return an *instance* of the configuration matching ``env``.

    Defaults to the value of ``FLASK_ENV`` and falls back to development.
    """
    env = (env or os.getenv("FLASK_ENV", "development")).lower()
    config_cls = _CONFIG_BY_NAME.get(env, DevelopmentConfig)
    return config_cls()
