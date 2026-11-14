from datetime import UTC, datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.enums import Edition, enum_column_type
from app.models.mixins import PublicIdMixin


class Board(PublicIdMixin, db.Model):
    """Een bord (project) van één team. Alle teamleden zien dit zelfde bord."""

    __tablename__ = "boards"
    __table_args__ = (
        # Het team moet bij dezelfde organisatie horen als het bord.
        ForeignKeyConstraint(
            ["team_id", "organisation_id"], ["teams.id", "teams.organisation_id"]
        ),
        UniqueConstraint("id", "organisation_id"),
        UniqueConstraint("team_id", "name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    organisation_id: Mapped[int] = mapped_column(index=True)
    team_id: Mapped[int] = mapped_column(index=True)
    name: Mapped[str] = mapped_column(String(80))
    edition: Mapped[Edition] = mapped_column(enum_column_type(Edition), default=Edition.TEAM)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    team: Mapped["Team"] = relationship(  # noqa: F821
        primaryjoin="Board.team_id == Team.id", foreign_keys=[team_id]
    )
    actions: Mapped[list["BoardAction"]] = relationship(  # noqa: F821
        back_populates="board",
        primaryjoin="Board.id == BoardAction.board_id",
        foreign_keys="BoardAction.board_id",
    )


class BoardAction(PublicIdMixin, db.Model):
    """Eén onderdeel van het bord: wanneer het startte en wanneer het klaar was.

    Er wordt geen invoertekst bewaard, alleen welk onderdeel, in welke fase en de tijden.
    Meerdere acties kunnen tegelijk lopen (completed_at is dan nog leeg).
    """

    __tablename__ = "board_actions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["board_id", "organisation_id"], ["boards.id", "boards.organisation_id"]
        ),
        UniqueConstraint("board_id", "component_key"),
        CheckConstraint("phase BETWEEN 1 AND 4", name="phase_range"),
        CheckConstraint(
            "completed_at IS NULL OR completed_at >= started_at", name="completed_after_start"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    organisation_id: Mapped[int] = mapped_column(index=True)
    board_id: Mapped[int] = mapped_column(index=True)
    component_key: Mapped[str] = mapped_column(String(40))
    phase: Mapped[int] = mapped_column(Integer)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    board: Mapped["Board"] = relationship(
        back_populates="actions",
        primaryjoin="BoardAction.board_id == Board.id",
        foreign_keys=[board_id],
    )

    @property
    def is_done(self) -> bool:
        return self.completed_at is not None
