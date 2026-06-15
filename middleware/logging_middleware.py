"""Logging configuration and lightweight request logging.

``configure_logging`` sets up a console handler with a structured-ish format
honouring ``LOG_LEVEL``. ``register_request_logging`` logs one line per request
with method, path, status and the authenticated user (if any).
"""
from __future__ import annotations

import logging
import sys
import time

from flask import g, request

_LOG_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"


def configure_logging(app) -> None:
    level = getattr(logging, app.config.get("LOG_LEVEL", "INFO"), logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(_LOG_FORMAT))

    root = logging.getLogger()
    root.setLevel(level)
    # Avoid duplicate handlers when the factory runs more than once (tests).
    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        root.addHandler(handler)

    app.logger.setLevel(level)


def register_request_logging(app) -> None:
    logger = logging.getLogger("request")

    @app.before_request
    def _start_timer():
        g._start_time = time.perf_counter()

    @app.after_request
    def _log_request(response):
        # Skip noisy static asset requests.
        if request.path.startswith("/static/"):
            return response
        from flask_login import current_user

        elapsed_ms = (time.perf_counter() - getattr(g, "_start_time", time.perf_counter())) * 1000
        user = getattr(current_user, "username", "anonymous") if current_user else "anonymous"
        logger.info(
            "%s %s -> %s (%.1f ms) user=%s",
            request.method, request.path, response.status_code, elapsed_ms, user,
        )
        return response
