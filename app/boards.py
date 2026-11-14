"""Borden en acties. Weet niets van HTTP; de routes roepen deze functies aan.

Regels:
- Alleen beheerders maken borden aan en hernoemen teams.
- Alleen gewone accounts (teamleden) starten en ronden onderdelen af, op het bord van hun eigen team.
- Een beheerder kijkt alleen mee.
"""

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app import clock
from app.accounts import get_or_create_team
from app.catalog import get_component
from app.extensions import db
from app.models import Board, BoardAction, Edition, Role, Team, User
from app.scoping import actions_visible_to, boards_visible_to, teams_visible_to


class BoardError(Exception):
    pass


class NotAllowed(BoardError):
    pass


class BoardNotFound(BoardError):
    pass


class TeamNotFound(BoardError):
    pass


class ActionNotFound(BoardError):
    pass


class UnknownComponent(BoardError):
    pass


class ActionAlreadyStarted(BoardError):
    pass


class ActionAlreadyDone(BoardError):
    pass


class BoardNameTaken(BoardError):
    pass


class TeamNameTaken(BoardError):
    pass


def _require_admin(user: User) -> None:
    if user.role is not Role.ADMIN:
        raise NotAllowed


def _require_member(user: User) -> None:
    if user.role is not Role.MEMBER:
        raise NotAllowed


def find_visible_board(user: User, public_id: str) -> Board | None:
    """Een bord dat deze gebruiker mag zien, anders None (ook als het bord wel bestaat)."""
    return db.session.scalar(boards_visible_to(user).where(Board.public_id == public_id))


def create_board(*, admin: User, team_name: str, board_name: str, edition: Edition) -> Board:
    """Maak een bord voor een team. Bestaat het team nog niet, dan wordt het aangemaakt."""
    _require_admin(admin)
    organisation_id = admin.organisation_id
    team = get_or_create_team(admin.organisation, team_name)
    board = Board(
        organisation_id=organisation_id,
        team_id=team.id,
        name=board_name.strip(),
        edition=edition,
    )
    db.session.add(board)
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise BoardNameTaken from exc
    return board


def rename_team(*, admin: User, team_public_id: str, new_name: str) -> Team:
    _require_admin(admin)
    team = db.session.scalar(teams_visible_to(admin).where(Team.public_id == team_public_id))
    if team is None:
        raise TeamNotFound
    clean_name = new_name.strip()
    taken = db.session.scalar(
        select(Team.id).where(
            Team.organisation_id == admin.organisation_id,
            func.lower(Team.name) == clean_name.lower(),
            Team.id != team.id,
        )
    )
    if taken is not None:
        raise TeamNameTaken
    team.name = clean_name
    db.session.commit()
    return team


def start_action(*, user: User, board_public_id: str, component_key: str) -> BoardAction:
    """Een teamlid start een onderdeel. Meerdere onderdelen mogen tegelijk lopen."""
    _require_member(user)
    board = find_visible_board(user, board_public_id)
    if board is None:
        raise BoardNotFound
    component = get_component(component_key)
    if component is None:
        raise UnknownComponent
    action = BoardAction(
        organisation_id=board.organisation_id,
        board_id=board.id,
        component_key=component.key,
        phase=component.phase,
        started_at=clock.utcnow(),
    )
    db.session.add(action)
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise ActionAlreadyStarted from exc
    return action


def complete_action(*, user: User, action_public_id: str) -> BoardAction:
    """Een teamlid rondt een lopend onderdeel af; het tijdstip bepaalt de duur."""
    _require_member(user)
    action = db.session.scalar(
        actions_visible_to(user).where(BoardAction.public_id == action_public_id).with_for_update()
    )
    if action is None:
        raise ActionNotFound
    if action.is_done:
        db.session.rollback()
        raise ActionAlreadyDone
    action.completed_at = clock.utcnow()
    db.session.commit()
    return action
