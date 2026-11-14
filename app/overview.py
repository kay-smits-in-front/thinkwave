"""Overzicht per team voor beheerders: alleen aantallen en namen, geen persoonsgegevens."""

from dataclasses import dataclass

from sqlalchemy import func, select

from app.catalog import COMPONENTS
from app.extensions import db
from app.models import Board, BoardAction, Role, Team, User
from app.scoping import actions_visible_to, boards_visible_to, teams_visible_to


@dataclass(frozen=True)
class BoardSummary:
    public_id: str
    name: str
    edition: str
    done: int
    active: int
    total: int


@dataclass(frozen=True)
class TeamOverview:
    public_id: str
    name: str
    member_count: int
    boards: list[BoardSummary]


def _member_counts(admin: User) -> dict[int, int]:
    rows = db.session.execute(
        select(User.team_id, func.count(User.id))
        .where(
            User.organisation_id == admin.organisation_id,
            User.role == Role.MEMBER,
            User.is_active.is_(True),
        )
        .group_by(User.team_id)
    )
    return {team_id: count for team_id, count in rows}


def _action_counts(admin: User) -> dict[int, tuple[int, int]]:
    """Per bord: (afgerond, lopend)."""
    counts: dict[int, tuple[int, int]] = {}
    for action in db.session.scalars(actions_visible_to(admin)):
        done, active = counts.get(action.board_id, (0, 0))
        counts[action.board_id] = (done + 1, active) if action.is_done else (done, active + 1)
    return counts


def team_overviews(admin: User) -> list[TeamOverview]:
    members = _member_counts(admin)
    actions = _action_counts(admin)
    boards_by_team: dict[int, list[Board]] = {}
    for board in db.session.scalars(boards_visible_to(admin).order_by(Board.name)):
        boards_by_team.setdefault(board.team_id, []).append(board)

    overviews = []
    for team in db.session.scalars(teams_visible_to(admin).order_by(Team.name)):
        summaries = []
        for board in boards_by_team.get(team.id, []):
            done, active = actions.get(board.id, (0, 0))
            summaries.append(
                BoardSummary(
                    public_id=board.public_id,
                    name=board.name,
                    edition=board.edition.value,
                    done=done,
                    active=active,
                    total=len(COMPONENTS),
                )
            )
        overviews.append(
            TeamOverview(
                public_id=team.public_id,
                name=team.name,
                member_count=members.get(team.id, 0),
                boards=summaries,
            )
        )
    return overviews
