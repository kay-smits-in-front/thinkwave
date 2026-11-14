import secrets

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column


def new_public_id() -> str:
    """Onraadbare verwijzing voor in URL's en formulieren (22 tekens, 128 bit)."""
    return secrets.token_urlsafe(16)


class PublicIdMixin:
    """Intern gebruiken we het getal 'id'; naar buiten toe alleen 'public_id'."""

    public_id: Mapped[str] = mapped_column(String(32), unique=True, default=new_public_id)
