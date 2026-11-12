"""Spelregels van het Thinkwave-bord, overgenomen uit de PlayCanvas-versie."""

import json
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from sqlalchemy import func, select

from app.extensions import db
from app.models import Action, Phase, Project, ProjectAction

CONTENT_PATH = Path(__file__).parent / "content" / "board.json"

# (maximale afstand tot de sweetspot, vermenigvuldiger) — zelfde trappen als het oude bord.
MULTIPLIER_STEPS = [(5, 2.0), (10, 1.2), (20, 1.0), (30, 0.8), (40, 0.5)]
FAR_MULTIPLIER = 0.2
INTERMISSIONS = 3  # evaluatiemomenten op 1/4, 2/4 en 3/4 van de tijdlijn


@cache
def load_content() -> dict:
    """Teksten van het bord: acties, evaluaties, eindschermen en tips."""
    return json.loads(CONTENT_PATH.read_text(encoding="utf-8"))


def seed_actions() -> int:
    """Zet de actiecatalogus uit board.json in de database. Bestaande namen worden bijgewerkt."""
    existing = {action.name: action for action in db.session.scalars(select(Action))}
    for data in load_content()["actions"]:
        action = existing.get(data["name"]) or Action(name=data["name"])
        for key, value in data.items():
            setattr(action, key, Phase(value) if key == "phase" else value)
        db.session.add(action)
    db.session.commit()
    return len(load_content()["actions"])


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


def perform(project: Project, action: Action) -> ProjectAction:
    """Voer een stap uit: de impact wordt berekend op de stand van dit moment."""
    if not can_perform(project, action):
        raise ValueError("Deze stap kan niet meer: geen beurten of geen tijd over.")
    step = ProjectAction(
        project=project,
        action=action,
        start_week=weeks_used(project),
        duration_weeks=action.duration_weeks,
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
    """Gemiddeld eigen oordeel per stap over alle projecten: de leerdata voor suggesties."""
    rows = db.session.execute(
        select(ProjectAction.action_id, func.avg(ProjectAction.self_rating))
        .where(ProjectAction.self_rating.is_not(None))
        .group_by(ProjectAction.action_id)
    )
    return {action_id: float(avg) for action_id, avg in rows}


def suggest(project: Project, limit: int = 3) -> list[Action]:
    """Volgende stappen: hoogste verwachte impact nu, bij gelijkspel wat anderen goed beoordeelden.

    shortcut: regels + gemiddelde beoordeling; vervang door een model zodra er genoeg afgeronde projecten zijn.
    """
    impacts = phase_impacts(project)
    ratings = average_ratings()
    actions = db.session.scalars(select(Action)).all()
    candidates = [a for a in actions if can_perform(project, a)]
    candidates.sort(key=lambda a: (-expected_impact(a, impacts), -ratings.get(a.id, 0), a.id))
    return candidates[:limit]


def tip_for(project: Project) -> dict:
    """Wisselende tip, op basis van het aantal gezette stappen."""
    tips = load_content()["tips"]
    return tips[len(project.steps) % len(tips)]
