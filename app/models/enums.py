"""Vaste keuzelijsten voor rollen en abonnementen."""

from enum import StrEnum

from sqlalchemy import Enum


class Role(StrEnum):
    ADMIN = "admin"
    MEMBER = "member"


class Edition(StrEnum):
    """De drie varianten van het bord: dezelfde werking, andere uitstraling en doelgroep."""

    YOUTH = "youth"
    TEAM = "team"
    EXECUTIVE = "executive"


EDITION_LABELS: dict[Edition, str] = {
    Edition.YOUTH: "Jeugd",
    Edition.TEAM: "Management en team",
    Edition.EXECUTIVE: "Directie",
}


class Plan(StrEnum):
    TEN = "ten"
    FIFTY = "fifty"
    UNLIMITED = "unlimited"


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
