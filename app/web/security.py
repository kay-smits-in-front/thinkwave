"""Beveiligingsheaders en foutpagina's. Foutpagina's tonen nooit details."""

from flask import Flask, Response, render_template, request
from werkzeug.exceptions import HTTPException

from app.extensions import db

# Geen JavaScript, geen externe bronnen, niet in een frame, formulieren alleen naar onszelf.
CONTENT_SECURITY_POLICY = (
    "default-src 'none'; "
    "style-src 'self'; "
    "img-src 'self'; "
    "form-action 'self'; "
    "base-uri 'none'; "
    "frame-ancestors 'none'"
)

ERROR_MESSAGES: dict[int, str] = {
    400: "Ongeldig verzoek.",
    403: "Geen toegang.",
    404: "Niet gevonden.",
    405: "Deze actie is niet toegestaan.",
    413: "Het verzoek is te groot.",
    429: "Te veel verzoeken. Probeer het later opnieuw.",
    500: "Er ging iets mis. Probeer het later opnieuw.",
}


def _add_security_headers(response: Response) -> Response:
    headers = response.headers
    headers["Content-Security-Policy"] = CONTENT_SECURITY_POLICY
    headers["X-Content-Type-Options"] = "nosniff"
    headers["X-Frame-Options"] = "DENY"
    headers["Referrer-Policy"] = "no-referrer"
    headers["Cross-Origin-Opener-Policy"] = "same-origin"
    headers["Cross-Origin-Resource-Policy"] = "same-origin"
    headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=()"
    if request.endpoint != "static":
        headers["Cache-Control"] = "no-store"
    return response


def _handle_error(error: Exception):
    code = error.code if isinstance(error, HTTPException) and error.code else 500
    if code >= 500:
        db.session.rollback()
    message = ERROR_MESSAGES.get(code, ERROR_MESSAGES[500])
    return render_template("error.html", code=code, message=message), code


def register_security(app: Flask) -> None:
    app.after_request(_add_security_headers)

    if app.config["SESSION_COOKIE_SECURE"]:

        @app.after_request
        def add_hsts(response: Response) -> Response:
            response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
            return response

    for code in ERROR_MESSAGES:
        app.register_error_handler(code, _handle_error)
