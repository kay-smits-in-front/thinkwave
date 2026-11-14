"""Configuratie uit omgevingsvariabelen. Geen geheimen in de code."""

from collections.abc import Mapping
from datetime import timedelta

MIN_SECRET_KEY_LENGTH = 32
DEV_SECRET_KEY = "local-development-only-change-me"
MAX_REQUEST_BYTES = 16_384  # Elke aanvraag is klein: formulieren met korte velden.


def normalise_database_url(url: str) -> str:
    """Zet een Render-achtige 'postgres://' URL om naar de SQLAlchemy-vorm met psycopg 3."""
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


def is_production(environ: Mapping[str, str]) -> bool:
    return environ.get("APP_ENV", "development").lower() == "production"


def find_production_problems(environ: Mapping[str, str]) -> list[str]:
    """Geef een lijst met ontbrekende of onveilige instellingen voor productie."""
    problems: list[str] = []
    secret_key = environ.get("SECRET_KEY", "")
    if len(secret_key) < MIN_SECRET_KEY_LENGTH or secret_key == DEV_SECRET_KEY:
        problems.append(f"SECRET_KEY (minimaal {MIN_SECRET_KEY_LENGTH} willekeurige tekens)")
    if not environ.get("DATABASE_URL", "").startswith(("postgres://", "postgresql://")):
        problems.append("DATABASE_URL (PostgreSQL)")
    if not environ.get("TRUSTED_HOSTS", "").strip():
        problems.append("TRUSTED_HOSTS (komma-gescheiden hostnamen)")
    if not environ.get("RATELIMIT_STORAGE_URI", "").startswith(("redis://", "rediss://")):
        problems.append("RATELIMIT_STORAGE_URI (Redis, gedeeld tussen workers)")
    return problems


def _hops(environ: Mapping[str, str]) -> int:
    value = environ.get("TRUSTED_PROXY_HOPS", "0").strip()
    return int(value) if value.isdigit() else 0


def build_config(environ: Mapping[str, str]) -> dict[str, object]:
    """Bouw de Flask-configuratie. In productie stopt dit bij onveilige instellingen."""
    production = is_production(environ)
    if production:
        problems = find_production_problems(environ)
        if problems:
            raise RuntimeError("Productie-instellingen ontbreken: " + ", ".join(problems))

    database_url = environ.get("DATABASE_URL", "sqlite:///thinkwave.db")
    config: dict[str, object] = {
        "SECRET_KEY": environ.get("SECRET_KEY") or DEV_SECRET_KEY,
        "SQLALCHEMY_DATABASE_URI": normalise_database_url(database_url),
        "SESSION_COOKIE_HTTPONLY": True,
        "SESSION_COOKIE_SAMESITE": "Lax",
        "SESSION_COOKIE_SECURE": production,
        # '__Host-' dwingt in de browser af: Secure, geen Domain, pad '/'.
        "SESSION_COOKIE_NAME": "__Host-session" if production else "session",
        "PERMANENT_SESSION_LIFETIME": timedelta(hours=8),
        "MAX_CONTENT_LENGTH": MAX_REQUEST_BYTES,
        "WTF_CSRF_TIME_LIMIT": 3600,
        "RATELIMIT_STORAGE_URI": environ.get("RATELIMIT_STORAGE_URI", "memory://"),
        "RATELIMIT_HEADERS_ENABLED": False,
        "TRUSTED_PROXY_HOPS": _hops(environ),
    }
    hosts = [h.strip() for h in environ.get("TRUSTED_HOSTS", "").split(",") if h.strip()]
    if hosts:
        config["TRUSTED_HOSTS"] = hosts
    return config
