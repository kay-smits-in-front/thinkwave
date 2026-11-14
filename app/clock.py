from datetime import UTC, datetime


def utcnow() -> datetime:
    """Eén plek voor 'nu', zodat tests de tijd kunnen vastzetten."""
    return datetime.now(UTC)
