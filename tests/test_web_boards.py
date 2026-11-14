import re
from datetime import UTC, datetime, timedelta

import pytest

from app import boards, clock
from app.extensions import db
from app.models import BoardAction, Edition, Plan
from tests.web_helpers import log_in, make_admin, make_board, make_member

T0 = datetime(2026, 3, 1, 9, 0, tzinfo=UTC)


@pytest.fixture
def now(monkeypatch):
    state = {"now": T0}
    monkeypatch.setattr(clock, "utcnow", lambda: state["now"])
    return state


def client_for(app, email):
    client = app.test_client()
    log_in(client, email)
    return client


def start(client, board, key="p1c1"):
    return client.post(f"/boards/{board.public_id}/start", data={"component_key": key})


def test_teammates_see_the_same_board_state(app):
    admin = make_admin()
    make_member(admin, "een@acme.nl")
    make_member(admin, "twee@acme.nl")
    board = make_board(admin)
    one, two = client_for(app, "een@acme.nl"), client_for(app, "twee@acme.nl")
    start(one, board, "p1c1")
    page = two.get(f"/boards/{board.public_id}").get_data(as_text=True)
    assert "bezig" in page and "Onderdeel 1.1" in page


def test_member_completes_action_and_duration_is_shown(app, now):
    admin = make_admin()
    make_member(admin)
    board = make_board(admin)
    client = client_for(app, "lid@acme.nl")
    start(client, board)
    action = db.session.query(BoardAction).one()
    now["now"] = T0 + timedelta(days=21)
    response = client.post(f"/boards/{board.public_id}/actions/{action.public_id}/complete")
    assert response.status_code == 302
    assert "klaar · 3 weken" in client.get(f"/boards/{board.public_id}").get_data(as_text=True)


def test_starting_same_component_twice_shows_message_not_error(app):
    admin = make_admin()
    make_member(admin)
    board = make_board(admin)
    client = client_for(app, "lid@acme.nl")
    start(client, board)
    response = client.post(
        f"/boards/{board.public_id}/start", data={"component_key": "p1c1"}, follow_redirects=True
    )
    assert response.status_code == 200 and b"al gestart" in response.data


def test_unknown_component_gives_400(app):
    admin = make_admin()
    make_member(admin)
    board = make_board(admin)
    client = client_for(app, "lid@acme.nl")
    assert start(client, board, "nope").status_code == 400
    assert start(client, board, "A" * 41).status_code == 400
    assert db.session.query(BoardAction).count() == 0


def test_member_gets_404_for_board_of_other_team_and_cannot_act_on_it(app):
    admin = make_admin()
    make_member(admin, "a@acme.nl", "Team A")
    make_member(admin, "b@acme.nl", "Team B")
    board_b = make_board(admin, "Team B")
    client = client_for(app, "a@acme.nl")
    assert client.get(f"/boards/{board_b.public_id}").status_code == 404
    assert start(client, board_b).status_code == 404
    assert db.session.query(BoardAction).count() == 0


def test_member_gets_404_for_board_of_other_organisation(app):
    admin_a = make_admin()
    make_member(admin_a, "a@acme.nl")
    admin_b = make_admin("Beta", "beheer@beta.nl")
    make_member(admin_b, "b@beta.nl")
    board_b = make_board(admin_b)
    client = client_for(app, "a@acme.nl")
    assert client.get(f"/boards/{board_b.public_id}").status_code == 404
    assert start(client, board_b).status_code == 404


def test_member_cannot_complete_action_of_other_team(app):
    admin = make_admin()
    make_member(admin, "a@acme.nl", "Team A")
    member_b = make_member(admin, "b@acme.nl", "Team B")
    board_b = make_board(admin, "Team B")
    boards.start_action(user=member_b, board_public_id=board_b.public_id, component_key="p1c1")
    action = db.session.query(BoardAction).one()
    client = client_for(app, "a@acme.nl")
    response = client.post(f"/boards/{board_b.public_id}/actions/{action.public_id}/complete")
    assert response.status_code == 404
    assert db.session.query(BoardAction).one().completed_at is None


def test_admin_can_view_every_board_of_own_organisation_but_not_act(app):
    admin = make_admin()
    make_member(admin, "a@acme.nl", "Team A")
    make_member(admin, "b@acme.nl", "Team B")
    board_a, board_b = make_board(admin, "Team A"), make_board(admin, "Team B")
    client = client_for(app, "beheer@acme.nl")
    for board in (board_a, board_b):
        page = client.get(f"/boards/{board.public_id}")
        assert page.status_code == 200 and b"alleen meekijken" in page.data
        assert start(client, board).status_code == 403


def test_admin_cannot_view_board_of_other_organisation(app):
    admin_a = make_admin()
    admin_b = make_admin("Beta", "beheer@beta.nl")
    board_b = make_board(admin_b)
    assert client_for(app, admin_a.email).get(f"/boards/{board_b.public_id}").status_code == 404


@pytest.mark.parametrize(("edition", "marker"), [
    (Edition.YOUTH, "theme-youth"), (Edition.TEAM, "theme-team"), (Edition.EXECUTIVE, "theme-executive"),
])
def test_each_edition_uses_its_own_theme(app, edition, marker):
    admin = make_admin()
    make_member(admin)
    board = make_board(admin, edition=edition)
    page = client_for(app, "lid@acme.nl").get(f"/boards/{board.public_id}").get_data(as_text=True)
    assert marker in page and f"css/{edition.value}.css" in page


def test_admin_overview_lists_teams_with_progress_for_whole_organisation_only(app):
    admin = make_admin()
    member = make_member(admin, "a@acme.nl", "Team A")
    make_member(admin, "b@acme.nl", "Team B")
    board = make_board(admin, "Team A", "Alpha")
    other = make_admin("Beta", "beheer@beta.nl")
    make_member(other, "x@beta.nl", "Geheim team")
    make_board(other, "Geheim team", "Geheim bord")
    boards.start_action(user=member, board_public_id=board.public_id, component_key="p1c1")

    page = client_for(app, "beheer@acme.nl").get("/admin/").get_data(as_text=True)
    assert "Team A" in page and "Team B" in page and "Alpha" in page
    assert "1 bezig" in page
    assert "Geheim" not in page


def test_admin_creates_board_and_renames_team(app):
    admin = make_admin()
    member = make_member(admin)
    client = client_for(app, "beheer@acme.nl")
    client.post("/admin/boards", data={"team_name": "Team A", "board_name": "Nieuw", "edition": "youth"})
    page = client.get("/admin/").get_data(as_text=True)
    assert "Nieuw" in page and "Jeugd" in page
    client.post(f"/admin/teams/{member.team.public_id}/rename", data={"name": "Vernieuwers"})
    assert "Vernieuwers" in client.get("/admin/").get_data(as_text=True)


def test_admin_cannot_rename_team_of_other_organisation(app):
    admin_a = make_admin()
    admin_b = make_admin("Beta", "beheer@beta.nl")
    member_b = make_member(admin_b, "b@beta.nl", "Team B")
    client = client_for(app, admin_a.email)
    response = client.post(f"/admin/teams/{member_b.team.public_id}/rename", data={"name": "Gekaapt"})
    assert response.status_code == 404
    assert member_b.team.name == "Team B"


def test_admin_adds_accounts_within_limit_and_multiple_admins(app):
    admin = make_admin(plan=Plan.TEN)
    client = client_for(app, "beheer@acme.nl")
    client.post("/admin/accounts/admins", data={"email": "tweede@acme.nl", "password": "een-lang-genoeg-wachtwoord"})
    for n in range(10):
        client.post("/admin/accounts/members", data={
            "email": f"lid{n}@acme.nl", "password": "een-lang-genoeg-wachtwoord", "team_name": "Team A"})
    refused = client.post("/admin/accounts/members", data={
        "email": "elf@acme.nl", "password": "een-lang-genoeg-wachtwoord", "team_name": "Team A"},
        follow_redirects=True)
    assert b"maximum aantal accounts" in refused.data
    second = app.test_client()
    assert log_in(second, "tweede@acme.nl").headers["Location"].endswith("/dashboard")
    assert second.get("/admin/").status_code == 200


def test_admin_can_deactivate_and_reactivate_but_not_self_or_foreign_accounts(app):
    admin = make_admin(plan=Plan.TEN)
    member = make_member(admin)
    other_member = make_member(make_admin("Beta", "beheer@beta.nl"), "b@beta.nl")
    client = client_for(app, "beheer@acme.nl")
    client.post(f"/admin/accounts/{member.public_id}/deactivate")
    assert member.is_active is False
    client.post(f"/admin/accounts/{member.public_id}/reactivate")
    assert member.is_active is True
    own = client.post(f"/admin/accounts/{admin.public_id}/deactivate", follow_redirects=True)
    assert b"eigen account" in own.data and admin.is_active is True
    assert client.post(f"/admin/accounts/{other_member.public_id}/deactivate").status_code == 404
    assert other_member.is_active is True


def test_reactivating_respects_seat_limit(app):
    admin = make_admin(plan=Plan.TEN)
    members = [make_member(admin, f"lid{n}@acme.nl") for n in range(10)]
    client = client_for(app, "beheer@acme.nl")
    client.post(f"/admin/accounts/{members[0].public_id}/deactivate")
    make_member(admin, "nieuw@acme.nl")
    response = client.post(f"/admin/accounts/{members[0].public_id}/reactivate", follow_redirects=True)
    assert b"maximum aantal accounts" in response.data
    assert members[0].is_active is False


# --- niets lekken in HTML ---


def test_pages_never_contain_hashes_internal_ids_or_other_peoples_emails(app):
    admin = make_admin()
    member = make_member(admin, "lid@acme.nl", "Team A")
    make_member(admin, "collega@acme.nl", "Team A")
    board = make_board(admin)
    boards.start_action(user=member, board_public_id=board.public_id, component_key="p1c1")
    action = db.session.query(BoardAction).one()

    admin_client = client_for(app, "beheer@acme.nl")
    member_client = client_for(app, "lid@acme.nl")
    pages = [
        member_client.get("/dashboard"),
        member_client.get(f"/boards/{board.public_id}"),
        admin_client.get("/admin/"),
        admin_client.get("/admin/accounts"),
        admin_client.get(f"/boards/{board.public_id}"),
    ]
    for response in pages:
        html = response.get_data(as_text=True)
        assert "scrypt" not in html and "pbkdf2" not in html
        assert "@acme.nl" not in html.replace("***@acme.nl", "")  # alleen afgeschermde adressen
        assert "collega@" not in html and "beheer@" not in html
        # interne getallen-ID's komen nergens in een URL of formulier
        assert not re.search(r"/(boards|teams|accounts|actions)/\d+(/|\")", html)
    assert action.public_id in pages[1].get_data(as_text=True)


def test_public_ids_are_long_and_random(app):
    admin = make_admin()
    ids = {make_board(admin, "Team A", f"Bord {n}").public_id for n in range(20)}
    assert len(ids) == 20 and all(len(i) >= 22 for i in ids)
