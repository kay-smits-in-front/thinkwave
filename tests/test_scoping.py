import pytest

from app.extensions import db
from app.models import Plan, Role
from app.scoping import teams_visible_to, users_visible_to
from tests.factories import make_org, make_team, make_user


@pytest.fixture
def world(app):
    """Twee organisaties; Acme heeft twee teams, Beta heeft er één."""
    acme = make_org("Acme", Plan.TEN)
    beta = make_org("Beta", Plan.TEN)
    acme_a = make_team(acme, "Team A")
    acme_b = make_team(acme, "Team B")
    beta_a = make_team(beta, "Team A")
    return {
        "acme_admin": make_user(acme, "admin@acme.nl", Role.ADMIN),
        "acme_a1": make_user(acme, "a1@acme.nl", Role.MEMBER, acme_a),
        "acme_a2": make_user(acme, "a2@acme.nl", Role.MEMBER, acme_a),
        "acme_b1": make_user(acme, "b1@acme.nl", Role.MEMBER, acme_b),
        "beta_admin": make_user(beta, "admin@beta.nl", Role.ADMIN),
        "beta_a1": make_user(beta, "a1@beta.nl", Role.MEMBER, beta_a),
    }


def emails(query) -> set[str]:
    return {user.email for user in db.session.scalars(query)}


def team_names(query) -> list[str]:
    return sorted(team.name for team in db.session.scalars(query))


def test_member_sees_only_own_team(world):
    assert emails(users_visible_to(world["acme_a1"])) == {"a1@acme.nl", "a2@acme.nl"}


def test_member_does_not_see_other_team_in_same_organisation(world):
    assert "b1@acme.nl" not in emails(users_visible_to(world["acme_a1"]))


def test_member_does_not_see_team_with_same_name_in_other_organisation(world):
    assert "a1@beta.nl" not in emails(users_visible_to(world["acme_a1"]))


def test_admin_sees_whole_own_organisation_and_nothing_else(world):
    assert emails(users_visible_to(world["acme_admin"])) == {
        "admin@acme.nl",
        "a1@acme.nl",
        "a2@acme.nl",
        "b1@acme.nl",
    }
    assert emails(users_visible_to(world["beta_admin"])) == {"admin@beta.nl", "a1@beta.nl"}


def test_member_sees_only_own_team_in_team_list(world):
    assert team_names(teams_visible_to(world["acme_b1"])) == ["Team B"]


def test_admin_sees_all_teams_of_own_organisation_only(world):
    assert team_names(teams_visible_to(world["acme_admin"])) == ["Team A", "Team B"]
    assert team_names(teams_visible_to(world["beta_admin"])) == ["Team A"]
