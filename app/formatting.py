from datetime import UTC, datetime, timedelta


def as_utc(value: datetime) -> datetime:
    """SQLite geeft tijden zonder zone terug; alles wat we opslaan is UTC."""
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def action_duration(started_at: datetime, completed_at: datetime | None, now: datetime) -> timedelta:
    """Looptijd van een onderdeel: tot het klaar was, anders tot nu."""
    return as_utc(completed_at or now) - as_utc(started_at)


def format_duration(duration: timedelta) -> str:
    days = duration.days
    if days < 1:
        return "minder dan 1 dag"
    if days < 14:
        return "1 dag" if days == 1 else f"{days} dagen"
    if days < 60:
        return f"{days // 7} weken"
    return f"{days // 30} maanden"


def mask_email(email: str) -> str:
    """'jan@acme.nl' wordt 'j***@acme.nl'. Zo staat er geen volledig adres in de pagina."""
    local, _, domain = email.partition("@")
    return f"{local[:1]}***@{domain}"
