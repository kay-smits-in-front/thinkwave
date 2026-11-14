from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.exc import IntegrityError

from app import accounts, boards, clock
from app.boards import (
    ActionAlreadyDone,
    ActionAlreadyStarted,
    ActionNotFound,
    BoardNameTaken,
    BoardNotFound,
    NotAllowed,
    TeamNameTaken,
    TeamNotFound,
    UnknownComponent,
)
from app.catalog import COMPONENTS, PHASE_NUMBERS, components_in_phase, get_component
from app.extensions import db
from app.models import BoardAction, Edition, Plan
from app.board_view import build_board_view
from tests.factories import PASSWORD

T0 = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)


@pytest.fixture
def now(monkeypatch):
    """Zet de klok vast en laat tests hem verzetten."""
    state = {"now": T0}
    monkeypatch.setattr(clock, "utcnow", lambda: state["now"])
    return state


def admin_of(name="Acme", email="beheer@acme.nl", plan=Plan.UNLIMITED):
    accounts.request_admin_account(email=email, password=PASSWORD, organisation_name=name)
    return accounts.approve_admin(email, plan)


def member_of(admin, email="lid@acme.nl", team="Team A"):
    return accounts.add_member(admin=admin, email=email, password=PASSWORD, team_name=team)


def board_for(admin, team="Team A", name="Project 1", edition=Edition.TEAM):
    return boards.create_board(admin=admin, team_name=team, board_name=name, edition=edition)


# --- catalogus ---


def test_catalog_has_four_phases_with_unique_keys():
    assert PHASE_NUMBERS == (1, 2, 3, 4)
    assert len({component.key for component in COMPONENTS}) == len(COMPONENTS)
    assert all(components_in_phase(phase) for phase in PHASE_NUMBERS)


def test_unknown_component_key_is_not_in_catalog():
    assert get_component("niet-bestaand") is None


# --- borden en teams ---


def test_admin_creates_board_and_team_in_one_step(app):
    admin = admin_of()
    board = board_for(admin, "Innovatie", "Nieuwe app", Edition.YOUTH)
    assert board.team.name == "Innovatie"
    assert board.edition is Edition.YOUTH
    assert board.organisation_id == admin.organisation_id


def test_board_reuses_existing_team(app):
    admin = admin_of()
    member = member_of(admin, team="Innovatie")
    board = board_for(admin, "innovatie")
    assert board.team_id == member.team_id


def test_board_name_must_be_unique_within_team(app):
    admin = admin_of()
    board_for(admin)
    with pytest.raises(BoardNameTaken):
        board_for(admin)


def test_member_cannot_create_board(app):
    admin = admin_of()
    member = member_of(admin)
    with pytest.raises(NotAllowed):
        board_for(member)


def test_admin_renames_team(app):
    admin = admin_of()
    member = member_of(admin)
    boards.rename_team(admin=admin, team_public_id=member.team.public_id, new_name="Nieuw")
    assert member.team.name == "Nieuw"


def test_rename_to_existing_team_name_is_refused(app):
    admin = admin_of()
    a = member_of(admin, "a@acme.nl", "Team A")
    member_of(admin, "b@acme.nl", "Team B")
    with pytest.raises(TeamNameTaken):
        boards.rename_team(admin=admin, team_public_id=a.team.public_id, new_name="team b")


def test_cannot_rename_team_of_other_organisation(app):
    admin_a = admin_of()
    admin_b = admin_of("Beta", "beheer@beta.nl")
    member_b = member_of(admin_b, "lid@beta.nl", "Team B")
    with pytest.raises(TeamNotFound):
        boards.rename_team(admin=admin_a, team_public_id=member_b.team.public_id, new_name="X")


# --- acties ---


def test_member_starts_and_completes_action_and_duration_is_stored_as_times(app, now):
    admin = admin_of()
    member = member_of(admin)
    board = board_for(admin)
    action = boards.start_action(user=member, board_public_id=board.public_id, component_key="p1c1")
    assert action.phase == 1
    assert action.completed_at is None

    now["now"] = T0 + timedelta(days=21)
    done = boards.complete_action(user=member, action_public_id=action.public_id)
    assert done.completed_at == now["now"] or done.completed_at.replace(tzinfo=UTC) == now["now"]


def test_several_actions_can_run_at_the_same_time(app, now):
    admin = admin_of()
    member = member_of(admin)
    board = board_for(admin)
    for key in ("p1c1", "p1c2", "p3c1"):
        boards.start_action(user=member, board_public_id=board.public_id, component_key=key)
    active = db.session.query(BoardAction).filter(BoardAction.completed_at.is_(None)).count()
    assert active == 3


def test_component_can_only_be_started_once_per_board(app):
    admin = admin_of()
    member = member_of(admin)
    board = board_for(admin)
    boards.start_action(user=member, board_public_id=board.public_id, component_key="p1c1")
    with pytest.raises(ActionAlreadyStarted):
        boards.start_action(user=member, board_public_id=board.public_id, component_key="p1c1")


def test_same_component_can_run_on_different_boards(app):
    admin = admin_of()
    member = member_of(admin)
    one = board_for(admin, name="Een")
    two = board_for(admin, name="Twee")
    boards.start_action(user=member, board_public_id=one.public_id, component_key="p1c1")
    boards.start_action(user=member, board_public_id=two.public_id, component_key="p1c1")


def test_unknown_component_is_refused(app):
    admin = admin_of()
    member = member_of(admin)
    board = board_for(admin)
    with pytest.raises(UnknownComponent):
        boards.start_action(user=member, board_public_id=board.public_id, component_key="'; DROP")


def test_action_cannot_be_completed_twice(app):
    admin = admin_of()
    member = member_of(admin)
    board = board_for(admin)
    action = boards.start_action(user=member, board_public_id=board.public_id, component_key="p2c1")
    boards.complete_action(user=member, action_public_id=action.public_id)
    with pytest.raises(ActionAlreadyDone):
        boards.complete_action(user=member, action_public_id=action.public_id)


def test_admin_cannot_start_or_complete_actions(app):
    admin = admin_of()
    member = member_of(admin)
    board = board_for(admin)
    action = boards.start_action(user=member, board_public_id=board.public_id, component_key="p1c1")
    with pytest.raises(NotAllowed):
        boards.start_action(user=admin, board_public_id=board.public_id, component_key="p1c2")
    with pytest.raises(NotAllowed):
        boards.complete_action(user=admin, action_public_id=action.public_id)


def test_member_cannot_touch_board_of_other_team(app):
    admin = admin_of()
    member_a = member_of(admin, "a@acme.nl", "Team A")
    member_of(admin, "b@acme.nl", "Team B")
    board_b = board_for(admin, "Team B")
    with pytest.raises(BoardNotFound):
        boards.start_action(user=member_a, board_public_id=board_b.public_id, component_key="p1c1")


def test_member_cannot_touch_board_of_other_organisation(app):
    admin_a = admin_of()
    member_a = member_of(admin_a)
    admin_b = admin_of("Beta", "beheer@beta.nl")
    member_b = member_of(admin_b, "lid@beta.nl", "Team A")
    board_b = board_for(admin_b, "Team A")
    action_b = boards.start_action(user=member_b, board_public_id=board_b.public_id, component_key="p1c1")
    with pytest.raises(BoardNotFound):
        boards.start_action(user=member_a, board_public_id=board_b.public_id, component_key="p1c2")
    with pytest.raises(ActionNotFound):
        boards.complete_action(user=member_a, action_public_id=action_b.public_id)


# --- database-regels ---


def test_database_refuses_completion_before_start(app):
    admin = admin_of()
    board = board_for(admin)
    db.session.add(
        BoardAction(
            organisation_id=board.organisation_id,
            board_id=board.id,
            component_key="p1c1",
            phase=1,
            started_at=T0,
            completed_at=T0 - timedelta(days=1),
        )
    )
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_database_refuses_phase_outside_one_to_four(app):
    admin = admin_of()
    board = board_for(admin)
    db.session.add(
        BoardAction(
            organisation_id=board.organisation_id,
            board_id=board.id,
            component_key="p9c9",
            phase=5,
            started_at=T0,
        )
    )
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_database_refuses_action_with_organisation_that_does_not_own_the_board(app):
    admin_a = admin_of()
    admin_b = admin_of("Beta", "beheer@beta.nl")
    board_a = board_for(admin_a)
    db.session.add(
        BoardAction(
            organisation_id=admin_b.organisation_id,
            board_id=board_a.id,
            component_key="p1c1",
            phase=1,
            started_at=T0,
        )
    )
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


# --- weergave ---


def test_board_view_shows_status_and_duration_per_component(app, now):
    admin = admin_of()
    member = member_of(admin)
    board = board_for(admin)
    first = boards.start_action(user=member, board_public_id=board.public_id, component_key="p1c1")
    boards.start_action(user=member, board_public_id=board.public_id, component_key="p1c2")
    now["now"] = T0 + timedelta(days=21)
    boards.complete_action(user=member, action_public_id=first.public_id)
    now["now"] = T0 + timedelta(days=30)

    phases = build_board_view(board)
    phase_one = {c.key: c for c in phases[0].components}
    assert phase_one["p1c1"].status == "done"
    assert phase_one["p1c1"].duration_text == "3 weken"
    assert phase_one["p1c2"].status == "active"
    assert phase_one["p1c2"].duration_text == "4 weken"
    assert phase_one["p1c3"].status == "todo"
    assert phases[0].done == 1
