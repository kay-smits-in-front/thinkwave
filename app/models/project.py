from datetime import UTC, datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.enums import Board, MeasureKind, NoteKind, enum_column_type

DEFAULT_TOTAL_WEEKS = 104  # 24 maanden, zoals de tijdlijn van het oude bord


def _now() -> datetime:
    return datetime.now(UTC)


class Project(db.Model):
    """Een innovatietraject van één organisatie, eventueel van één team."""

    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    organisation_id: Mapped[int] = mapped_column(ForeignKey("organisations.id"), index=True)
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    goal: Mapped[str] = mapped_column(Text, default="")
    board: Mapped[Board] = mapped_column(enum_column_type(Board), default=Board.WORK)
    total_weeks: Mapped[int] = mapped_column(default=DEFAULT_TOTAL_WEEKS)
    self_rating: Mapped[int | None]  # eindoordeel 1-5, om succesvolle trajecten te herkennen
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    steps: Mapped[list["ProjectAction"]] = relationship(
        back_populates="project", order_by="ProjectAction.start_week", cascade="all, delete-orphan"
    )
    measurements: Mapped[list["Measurement"]] = relationship(
        order_by="Measurement.created_at.desc()", cascade="all, delete-orphan"
    )
    notes: Mapped[list["Note"]] = relationship(
        order_by="Note.created_at.desc()", cascade="all, delete-orphan"
    )
    checklist: Mapped[list["ChecklistItem"]] = relationship(
        order_by="ChecklistItem.id", cascade="all, delete-orphan"
    )


class ProjectAction(db.Model):
    """Een uitgevoerde stap: wanneer, hoe lang, wat het opleverde en hoe goed het ging."""

    __tablename__ = "project_actions"
    __table_args__ = (
        CheckConstraint("self_rating IS NULL OR self_rating BETWEEN 1 AND 5", name="rating_1_5"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    action_id: Mapped[int] = mapped_column(ForeignKey("actions.id"), index=True)
    start_week: Mapped[int]
    duration_weeks: Mapped[int]
    impact_percent: Mapped[float]
    result: Mapped[str] = mapped_column(Text, default="")
    self_rating: Mapped[int | None]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    project: Mapped[Project] = relationship(back_populates="steps")
    action: Mapped["Action"] = relationship()  # noqa: F821


class Measurement(db.Model):
    __tablename__ = "measurements"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    kind: Mapped[MeasureKind] = mapped_column(enum_column_type(MeasureKind))
    value: Mapped[float]
    note: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Note(db.Model):
    """Een idee of een verslag."""

    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    kind: Mapped[NoteKind] = mapped_column(enum_column_type(NoteKind))
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ChecklistItem(db.Model):
    __tablename__ = "checklist_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    text: Mapped[str] = mapped_column(String(255))
    done: Mapped[bool] = mapped_column(Boolean, default=False)
