"""Vaste keuzelijsten voor rollen en abonnementen."""

from enum import StrEnum

from sqlalchemy import Enum


class Role(StrEnum):
    ADMIN = "admin"
    MEMBER = "member"


class Plan(StrEnum):
    TEN = "ten"
    FIFTY = "fifty"
    UNLIMITED = "unlimited"


class Phase(StrEnum):
    RESEARCH = "research"
    IDEATION = "ideation"
    DEVELOPMENT = "development"
    BUSINESS = "business"


class Board(StrEnum):
    """Drie borden op dezelfde data; alleen weergave en toon verschillen."""

    YOUTH = "youth"
    WORK = "work"
    MANAGEMENT = "management"


class MeasureKind(StrEnum):
    """Telbare dingen die je normaal niet meet."""

    IDEAS = "ideas"
    BUDGET = "budget"
    PROBLEMS_SOLVED = "problems_solved"
    RESEARCH_HOURS = "research_hours"
    PEOPLE_SPOKEN = "people_spoken"
    INTERNS_HIRED = "interns_hired"
    OTHER = "other"


class NoteKind(StrEnum):
    IDEA = "idea"
    REPORT = "report"


SEAT_LIMITS: dict[Plan, int | None] = {
    Plan.TEN: 10,
    Plan.FIFTY: 50,
    Plan.UNLIMITED: None,
}


def enum_column_type(enum_class: type[StrEnum]) -> Enum:
    """Sla de waarde ('admin') op in de database, niet de naam ('ADMIN')."""
    return Enum(
        enum_class,
        native_enum=False,
        length=20,
        values_callable=lambda members: [member.value for member in members],
    )
