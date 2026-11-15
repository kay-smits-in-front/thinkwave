"""Beveiliging die voor elk verzoek geldt: rate limiting, security headers en nette foutpagina's."""

import time
from collections import defaultdict, deque

from flask import Flask, Response, current_app, g, render_template, request

# (endpoint-voorvoegsel, maximaal aantal POST-verzoeken, per zoveel seconden) per IP-adres.
# Een schoolklas deelt vaak één IP-adres, daarom zijn de IP-limieten ruim.
POST_LIMITS = [
    ("auth.submit_login", 100, 60),
    ("registration.submit_registration", 20, 3600),
    ("", 300, 60),  # alle overige formulieren
]
LOGIN_ATTEMPTS_PER_ACCOUNT = (10, 600)  # per IP + e-mailadres: tegen wachtwoord raden

CONTENT_SECURITY_POLICY = "; ".join(
    [
        "default-src 'self'",
        "script-src 'self' https://unpkg.com",
        # HTMX en de templates gebruiken style-attributen (bijv. --i voor de positie in de ring).
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
        "font-src https://fonts.gstatic.com",
        "img-src 'self' data:",
        "connect-src 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
        "base-uri 'none'",
        "object-src 'none'",
    ]
)


class RateLimiter:
    """Telt verzoeken per sleutel in een schuivend tijdvenster.

    shortcut: geheugen per proces (gunicorn draait 2 workers, dus de echte limiet is maximaal 2x);
    vervang door Redis zodra er meer instances draaien.
    """

    def __init__(self) -> None:
        self.hits: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str, limit: int, window: int) -> bool:
        now = time.monotonic()
        hits = self.hits[key]
        while hits and hits[0] <= now - window:
            hits.popleft()
        if len(hits) >= limit:
            return False
        hits.append(now)
        return True


def limit_for(endpoint: str) -> tuple[str, int, int]:
    """De eerste regel waarvan het voorvoegsel past; de laatste regel ('') past altijd."""
    return next(rule for rule in POST_LIMITS if endpoint.startswith(rule[0]))


def check_rate_limit():
    """Weiger te veel formulieren vanaf één IP-adres (brute force, spam, scripts)."""
    if request.method != "POST" or not request.endpoint:
        return None
    limiter = current_app.extensions["rate_limiter"]
    prefix, limit, window = limit_for(request.endpoint)
    allowed = limiter.allow(f"{request.remote_addr}:{prefix or 'post'}", limit, window)
    if allowed and request.endpoint == "auth.submit_login":
        email = request.form.get("email", "").strip().lower()[:254]
        allowed = limiter.allow(f"{request.remote_addr}:login:{email}", *LOGIN_ATTEMPTS_PER_ACCOUNT)
    return None if allowed else error_page(429)


def add_security_headers(response: Response) -> Response:
    response.headers["Content-Security-Policy"] = CONTENT_SECURITY_POLICY
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    if request.is_secure or request.headers.get("X-Forwarded-Proto") == "https":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    if getattr(g, "user", None) is not None:
        response.headers["Cache-Control"] = "no-store"  # geen projectdata in gedeelde caches
    return response


ERROR_MESSAGES = {
    400: "Het formulier klopt niet of is verlopen. Laad de pagina opnieuw.",
    403: "Je hebt geen toegang tot deze pagina.",
    404: "Deze pagina bestaat niet of je hebt er geen toegang toe.",
    405: "Deze actie is hier niet toegestaan.",
    413: "Wat je verstuurt is te groot.",
    429: "Te veel pogingen. Wacht even en probeer het opnieuw.",
    500: "Er ging iets mis aan onze kant. Probeer het later opnieuw.",
}


def error_page(code: int, message: str | None = None):
    """Foutpagina zonder technische details, zodat er niets over de app uitlekt."""
    return render_template("error.html", code=code, message=message or ERROR_MESSAGES[code]), code


def init_security(app: Flask) -> None:
    app.extensions["rate_limiter"] = RateLimiter()
    app.before_request(check_rate_limit)
    app.after_request(add_security_headers)
    for code in ERROR_MESSAGES:
        app.register_error_handler(code, lambda _error, code=code: error_page(code))
