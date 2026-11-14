"""Bepaalt wat een gebruiker mag zien. Elke query voor klantdata hoort hier doorheen.

Regel: een beheerder ziet zijn eigen organisatie, een gewoon account alleen zijn eigen team.
Nooit data van een andere organisatie.
"""

from sqlalchemy import Select, select

from app.models import Board, BoardAction, Role, Team, User


def users_visible_to(user: User) -> Select[tuple[User]]:
    query = select(User).where(User.organisation_id == user.organisation_id)
    if user.role is Role.ADMIN:
        return query
    return query.where(User.team_id == user.team_id)


def teams_visible_to(user: User) -> Select[tuple[Team]]:
    query = select(Team).where(Team.organisation_id == user.organisation_id)
    if user.role is Role.ADMIN:
        return query
    return query.where(Team.id == user.team_id)


def boards_visible_to(user: User) -> Select[tuple[Board]]:
    query = select(Board).where(Board.organisation_id == user.organisation_id)
    if user.role is Role.ADMIN:
        return query
    return query.where(Board.team_id == user.team_id)


def actions_visible_to(user: User) -> Select[tuple[BoardAction]]:
    query = (
        select(BoardAction)
        .join(Board, BoardAction.board_id == Board.id)
        .where(
            BoardAction.organisation_id == user.organisation_id,
            Board.organisation_id == user.organisation_id,
        )
    )
    if user.role is Role.ADMIN:
        return query
    return query.where(Board.team_id == user.team_id)
