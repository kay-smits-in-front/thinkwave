from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.mixins import PublicIdMixin


class Team(PublicIdMixin, db.Model):
    """Een team binnen één organisatie. Gewone accounts zien alleen hun eigen team."""

    __tablename__ = "teams"
    __table_args__ = (
        UniqueConstraint("organisation_id", "name"),
        # Nodig zodat een User de combinatie (team, organisatie) kan afdwingen.
        UniqueConstraint("id", "organisation_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    organisation_id: Mapped[int] = mapped_column(ForeignKey("organisations.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))

    organisation: Mapped["Organisation"] = relationship(back_populates="teams")  # noqa: F821
    users: Mapped[list["User"]] = relationship(  # noqa: F821
        back_populates="team",
        primaryjoin="User.team_id == Team.id",
        foreign_keys="User.team_id",
    )
