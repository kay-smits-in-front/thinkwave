"""Zet een bord om naar een eenvoudige structuur voor de pagina.

Alleen tekst voor weergave en onzichtbare ID's; geen interne getallen of persoonsgegevens.
"""

from dataclasses import dataclass

from sqlalchemy import select

from app import clock
from app.catalog import COMPONENTS, PHASE_LABELS, PHASE_NUMBERS
from app.extensions import db
from app.formatting import action_duration, format_duration
from app.models import Board, BoardAction


@dataclass(frozen=True)
class ComponentView:
    key: str
    label: str
    status: str  # "todo", "active" of "done"
    action_public_id: str | None
    duration_text: str | None


@dataclass(frozen=True)
class PhaseView:
    number: int
    label: str
    components: list[ComponentView]
    done: int
    total: int


def build_board_view(board: Board) -> list[PhaseView]:
    """De gebruiker moet het bord al mogen zien; dit controleert dat niet opnieuw."""
    now = clock.utcnow()
    actions = db.session.scalars(select(BoardAction).where(BoardAction.board_id == board.id))
    by_key = {action.component_key: action for action in actions}

    phases = []
    for number in PHASE_NUMBERS:
        components = []
        for component in (c for c in COMPONENTS if c.phase == number):
            action = by_key.get(component.key)
            if action is None:
                view = ComponentView(component.key, component.label, "todo", None, None)
            else:
                duration = action_duration(action.started_at, action.completed_at, now)
                status = "done" if action.is_done else "active"
                view = ComponentView(
                    component.key,
                    component.label,
                    status,
                    action.public_id,
                    format_duration(duration),
                )
            components.append(view)
        done = sum(1 for c in components if c.status == "done")
        phases.append(PhaseView(number, PHASE_LABELS[number], components, done, len(components)))
    return phases
