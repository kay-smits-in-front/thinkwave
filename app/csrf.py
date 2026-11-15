"""CSRF-bescherming: elk formulier en HTMX-verzoek stuurt een geheim token uit de sessie mee."""

import secrets

from flask import abort, request, session

FIELD = "csrf_token"
HEADER = "X-CSRF-Token"


def csrf_token() -> str:
    """Het token van deze sessie; wordt aangemaakt bij het eerste gebruik."""
    if FIELD not in session:
        session[FIELD] = secrets.token_urlsafe(32)
    return session[FIELD]


def check_csrf() -> None:
    """Weiger elke POST zonder geldig token."""
    if request.method != "POST":
        return
    sent = request.form.get(FIELD) or request.headers.get(HEADER, "")
    if not secrets.compare_digest(sent.encode(), session.get(FIELD, "").encode()):  # bytes: ook niet-ASCII geeft 400, geen 500
        abort(400)
