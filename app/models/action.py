from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db
from app.models.enums import Phase, enum_column_type


class Action(db.Model):
    """Een stap uit de catalogus van het bord, bijvoorbeeld 'Expert Interview'."""

    __tablename__ = "actions"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    phase: Mapped[Phase] = mapped_column(enum_column_type(Phase), index=True)
    base_percent: Mapped[float]
    sweetspot: Mapped[int]  # fase-impact (%) waarop deze stap het meest oplevert
    duration_weeks: Mapped[int]
    impact: Mapped[str] = mapped_column(String(20))  # low, medium, high
    description: Mapped[str] = mapped_column(Text)
    max_uses: Mapped[int]
    url: Mapped[str | None] = mapped_column(String(500))
    image: Mapped[str | None] = mapped_column(String(120))
