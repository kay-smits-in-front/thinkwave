import pytest
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Organisation, Plan, Role, Team, User

PASSWORD = "een-lang-genoeg-wachtwoord"


def make_org(name: str, plan: Plan | None = None) -> Organisation:
    org = Organisation(name=name, plan=plan)
    db.session.add(org)
    db.session.flush()
    return org


def make_team(org: Organisation, name: str = "Team A") -> Team:
    team = Team(organisation_id=org.id, name=name)
    db.session.add(team)
    db.session.flush()
    return team


def make_user(org: Organisation, email: str, role: Role, team: Team | None = None) -> User:
    user = User(
        email=email,
        role=role,
        organisation_id=org.id,
        team_id=team.id if team else None,
    )
    user.set_password(PASSWORD)
    db.session.add(user)
    db.session.flush()
    return user


@pytest.mark.parametrize(
    ("plan", "limit"),
    [(None, 0), (Plan.TEN, 10), (Plan.FIFTY, 50), (Plan.UNLIMITED, None)],
)
def test_seat_limit_per_plan(app, plan, limit):
    assert make_org("Acme", plan).seat_limit() == limit


def test_email_is_stored_lowercase_and_trimmed(app):
    org = make_org("Acme")
    user = make_user(org, "  Kay@Example.COM ", Role.ADMIN)
    assert user.email == "kay@example.com"


def test_email_must_be_unique(app):
    org = make_org("Acme")
    make_user(org, "a@example.com", Role.ADMIN)
    with pytest.raises(IntegrityError):
        make_user(org, "A@example.com", Role.ADMIN)


def test_password_is_hashed_and_checked(app):
    user = make_user(make_org("Acme"), "a@example.com", Role.ADMIN)
    assert user.password_hash != PASSWORD
    assert user.check_password(PASSWORD)
    assert not user.check_password("verkeerd-wachtwoord")


def test_short_password_is_refused(app):
    user = User(email="a@example.com", organisation_id=1)
    with pytest.raises(ValueError):
        user.set_password("kort")


def test_admin_does_not_need_a_team(app):
    user = make_user(make_org("Acme"), "a@example.com", Role.ADMIN)
    assert user.team_id is None


def test_member_without_team_is_refused_by_database(app):
    org = make_org("Acme")
    with pytest.raises(IntegrityError):
        make_user(org, "m@example.com", Role.MEMBER)


def test_member_cannot_join_team_of_another_organisation(app):
    org_a = make_org("Acme")
    org_b = make_org("Beta")
    foreign_team = make_team(org_b)
    with pytest.raises(IntegrityError):
        make_user(org_a, "m@example.com", Role.MEMBER, foreign_team)


def test_member_in_own_team_is_accepted(app):
    org = make_org("Acme")
    team = make_team(org)
    user = make_user(org, "m@example.com", Role.MEMBER, team)
    assert user.team.name == "Team A"


def test_team_name_is_unique_within_organisation_only(app):
    org_a = make_org("Acme")
    org_b = make_org("Beta")
    make_team(org_a, "Innovatie")
    make_team(org_b, "Innovatie")
    with pytest.raises(IntegrityError):
        make_team(org_a, "Innovatie")
