"""Centralized error handling.

Translates domain exceptions and common HTTP errors into:
    * JSON ``{"error": ...}`` responses for ``/api/*`` requests, and
    * user-friendly flash + redirect (or an error page) for browser requests.

Crucially, it also rolls back the SQLAlchemy session on any unhandled error so
a failed multi-step transaction never leaks half-applied changes.
"""
from __future__ import annotations

import logging

from flask import flash, jsonify, redirect, render_template, request, url_for
from werkzeug.exceptions import HTTPException

from database.db import db
from services.exceptions import DomainError

logger = logging.getLogger(__name__)


def _wants_json() -> bool:
    return request.path.startswith("/api/") or request.accept_mimetypes.best == "application/json"


def register_error_handlers(app) -> None:
    @app.errorhandler(DomainError)
    def handle_domain_error(exc: DomainError):
        # Business-rule failures are expected; roll back and inform the user.
        db.session.rollback()
        logger.info("Domain error (%s): %s", type(exc).__name__, exc.message)
        if _wants_json():
            return jsonify({"error": exc.message}), exc.http_status
        flash(exc.message, "danger")
        return redirect(request.referrer or url_for("dashboard.index"))

    @app.errorhandler(HTTPException)
    def handle_http_exception(exc: HTTPException):
        if _wants_json():
            return jsonify({"error": exc.description}), exc.code
        if exc.code == 404:
            return render_template("errors/404.html"), 404
        return render_template("errors/generic.html", error=exc), exc.code or 500

    @app.errorhandler(Exception)
    def handle_unexpected(exc: Exception):
        # Unknown failure: roll back, log with stack trace, hide internals.
        db.session.rollback()
        logger.exception("Unhandled exception: %s", exc)
        if _wants_json():
            return jsonify({"error": "Error interno del servidor."}), 500
        return render_template("errors/generic.html", error=exc), 500
