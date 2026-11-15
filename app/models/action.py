from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db
from app.models.enums import Phase, enum_column_type


class Action(db.Model):
    """Een taak van het bord, bijvoorbeeld 'Expert Interview'.

    organisation_id leeg = de standaardset. Past een organisatie een taak aan, dan krijgt ze
    een eigen kopie (organisation_id gevuld, base_action_id wijst naar de standaardtaak).
    """

    __tablename__ = "actions"

    id: Mapped[int] = mapped_column(primary_key=True)
    organisation_id: Mapped[int | None] = mapped_column(ForeignKey("organisations.id"), index=True)
    base_action_id: Mapped[int | None] = mapped_column(ForeignKey("actions.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    phase: Mapped[Phase] = mapped_column(enum_column_type(Phase), index=True)
    base_percent: Mapped[float]
    sweetspot: Mapped[int]  # fase-impact (%) waarop deze taak het meest oplevert
    duration_weeks: Mapped[int]
    impact: Mapped[str] = mapped_column(String(20))  # low, medium, high
    description: Mapped[str] = mapped_column(Text)
    max_uses: Mapped[int]
    url: Mapped[str | None] = mapped_column(String(500))
    image: Mapped[str | None] = mapped_column(String(120))
    icon: Mapped[str | None] = mapped_column(String(120))

    @property
    def base_id(self) -> int:
        """Id van de standaardtaak; zo tellen beoordelingen van alle kopieën samen."""
        return self.base_action_id or self.id
