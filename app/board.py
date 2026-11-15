"""Spelregels van het Thinkwave-bord, overgenomen uit de PlayCanvas-versie."""

import json
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from sqlalchemy import func, select

from app.extensions import db
from app.models import Action, Board, Phase, Project, ProjectAction

CONTENT_PATH = Path(__file__).parent / "content" / "board.json"

# (maximale afstand tot de sweetspot, vermenigvuldiger) — zelfde trappen als het oude bord.
MULTIPLIER_STEPS = [(5, 2.0), (10, 1.2), (20, 1.0), (30, 0.8), (40, 0.5)]
FAR_MULTIPLIER = 0.2
INTERMISSIONS = 3  # evaluatiemomenten op 1/4, 2/4 en 3/4 van de tijdlijn
EDITABLE_FIELDS = ("name", "description", "duration_weeks")
MAX_WEEKS = 104


@cache
def load_content() -> dict:
    """Teksten van het bord: acties, evaluaties, eindschermen en tips."""
    return json.loads(CONTENT_PATH.read_text(encoding="utf-8"))


def seed_actions() -> int:
    """Zet de actiecatalogus uit board.json in de database. Bestaande namen worden bijgewerkt."""
    defaults = select(Action).where(Action.organisation_id.is_(None))
    existing = {action.name: action for action in db.session.scalars(defaults)}
    for data in load_content()["actions"]:
        action = existing.get(data["name"]) or Action(name=data["name"])
        for key, value in data.items():
            setattr(action, key, Phase(value) if key == "phase" else value)
        db.session.add(action)
    db.session.commit()
    return len(load_content()["actions"])


def default_actions() -> list[Action]:
    return list(db.session.scalars(select(Action).where(Action.organisation_id.is_(None)).order_by(Action.id)))


def organisation_actions(organisation_id: int) -> list[Action]:
    """De standaardset, met de eigen versie van de organisatie waar die bestaat."""
    copies = db.session.scalars(select(Action).filter_by(organisation_id=organisation_id))
    by_base = {copy.base_action_id: copy for copy in copies}
    return [by_base.get(action.id, action) for action in default_actions()]


def catalog(project: Project) -> list[Action]:
    """Taken op het bord van dit project. Het jeugdbord gebruikt altijd de standaardset."""
    if project.board is Board.YOUTH:
        return default_actions()
    return organisation_actions(project.organisation_id)


def editable_copy(action: Action, organisation_id: int) -> Action:
    """De versie van de organisatie om te bewerken; maakt een kopie van de standaardtaak als dat nodig is."""
    if action.organisation_id == organisation_id:
        return action
    copy = Action(organisation_id=organisation_id, base_action_id=action.id)
    for column in Action.__table__.columns.keys():
        if column not in {"id", "organisation_id", "base_action_id"}:
            setattr(copy, column, getattr(action, column))
    db.session.add(copy)
    return copy


def multiplier(phase_impact: float, sweetspot: int) -> float:
    """Hoe dichter de fase bij de sweetspot van een stap zit, hoe meer de stap oplevert."""
    distance = abs(phase_impact - sweetspot)
    return next((m for limit, m in MULTIPLIER_STEPS if distance < limit), FAR_MULTIPLIER)


def phase_impacts(project: Project) -> dict[Phase, float]:
    """Opgebouwde impact per fase in procenten, maximaal 100."""
    totals = {phase: 0.0 for phase in Phase}
    for step in project.steps:
        totals[step.action.phase] += step.impact_percent
    return {phase: min(total, 100.0) for phase, total in totals.items()}


def expected_impact(action: Action, impacts: dict[Phase, float]) -> float:
    return round(action.base_percent * multiplier(impacts[action.phase], action.sweetspot), 1)


def weeks_used(project: Project) -> int:
    return sum(step.duration_weeks for step in project.steps)


def uses_left(project: Project, action: Action) -> int:
    used = sum(1 for step in project.steps if step.action_id == action.id)
    return action.max_uses - used


def can_perform(project: Project, action: Action) -> bool:
    return uses_left(project, action) > 0 and weeks_used(project) < project.total_weeks


def perform(project: Project, action: Action, duration_weeks: int | None = None) -> ProjectAction:
    """Voer een taak uit: de impact wordt berekend op de stand van dit moment."""
    if not can_perform(project, action):
        raise ValueError("Deze taak kan niet meer: geen beurten of geen tijd over.")
    step = ProjectAction(
        project=project,
        action=action,
        start_week=weeks_used(project),
        duration_weeks=duration_weeks or action.duration_weeks,
        impact_percent=expected_impact(action, phase_impacts(project)),
    )
    db.session.add(step)
    db.session.commit()
    return step


def intermissions_passed(project: Project) -> int:
    """Hoeveel evaluatiemomenten (kwarten van de tijdlijn) al voorbij zijn, 0 tot 3."""
    quarters = weeks_used(project) * 4 // project.total_weeks
    return min(quarters, INTERMISSIONS)


@dataclass(frozen=True)
class Feedback:
    title: str
    text: str


def _first_match(rows: list[dict], impacts: dict[Phase, float]) -> dict:
    """Eerste regel waarvan de fase onder de drempel zit, anders de regel zonder fase."""
    for row in rows:
        if row["phase"] and impacts[Phase(row["phase"])] < row["threshold"]:
            return row
    return next(row for row in rows if row["phase"] is None)


def intermission_feedback(project: Project) -> Feedback | None:
    """Feedback van het laatst gepasseerde evaluatiemoment."""
    number = intermissions_passed(project)
    if number == 0:
        return None
    rows = [r for r in load_content()["intermissions"] if r["number"] == number]
    row = _first_match(rows, phase_impacts(project))
    return Feedback(row["title"], row["text"])


def ending(project: Project) -> Feedback | None:
    """Eindscherm zodra de tijdlijn vol is."""
    if weeks_used(project) < project.total_weeks:
        return None
    row = _first_match(load_content()["endings"], phase_impacts(project))
    return Feedback(row["header"], row["text"])


def average_ratings() -> dict[int, float]:
    """Gemiddeld eigen oordeel per standaardtaak over alle projecten: de leerdata voor suggesties."""
    base_id = func.coalesce(Action.base_action_id, Action.id)
    rows = db.session.execute(
        select(base_id, func.avg(ProjectAction.self_rating))
        .join(Action, ProjectAction.action_id == Action.id)
        .where(ProjectAction.self_rating.is_not(None))
        .group_by(base_id)
    )
    return {action_id: float(avg) for action_id, avg in rows}


def suggest(project: Project, limit: int = 3, exclude: Action | None = None) -> list[Action]:
    """Volgende stappen: hoogste verwachte impact nu, bij gelijkspel wat anderen goed beoordeelden.

    shortcut: regels + gemiddelde beoordeling; vervang door een model zodra er genoeg afgeronde projecten zijn.
    """
    impacts = phase_impacts(project)
    ratings = average_ratings()
    candidates = [a for a in catalog(project) if a is not exclude and can_perform(project, a)]
    candidates.sort(key=lambda a: (-expected_impact(a, impacts), -ratings.get(a.base_id, 0), a.base_id))
    return candidates[:limit]


def tip_for(project: Project) -> dict:
    """Wisselende tip, op basis van het aantal gezette stappen."""
    tips = load_content()["tips"]
    return tips[len(project.steps) % len(tips)]
