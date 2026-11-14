import pytest

from app import accounts
from app.accounts import (
    EmailAlreadyUsed,
    NotAnAdmin,
    OrganisationNameTaken,
    SeatLimitReached,
    UnknownAdmin,
)
from app.extensions import db
from app.models import Plan, Role, User
from tests.factories import PASSWORD, make_org, make_team, make_user


def request_admin(email="beheer@acme.nl", organisation="Acme"):
    return accounts.request_admin_account(
        email=email, password=PASSWORD, organisation_name=organisation
    )


def approved_admin(plan=Plan.TEN, email="beheer@acme.nl", organisation="Acme"):
    request_admin(email, organisation)
    return accounts.approve_admin(email, plan)


def add(admin, email, team="Team A"):
    return accounts.add_member(admin=admin, email=email, password=PASSWORD, team_name=team)


# --- inloggen ---


def test_authenticate_accepts_correct_credentials(app):
    admin = approved_admin()
    assert accounts.authenticate("BEHEER@acme.nl", PASSWORD) is admin


@pytest.mark.parametrize(
    ("email", "password"),
    [("beheer@acme.nl", "verkeerd-wachtwoord"), ("onbekend@acme.nl", PASSWORD)],
)
def test_authenticate_refuses_wrong_credentials(app, email, password):
    approved_admin()
    assert accounts.authenticate(email, password) is None


def test_authenticate_refuses_account_that_is_not_active(app):
    request_admin()
    assert accounts.authenticate("beheer@acme.nl", PASSWORD) is None


# --- beheerdersaanvraag en goedkeuren ---


def test_admin_request_creates_inactive_admin_without_plan(app):
    admin = request_admin()
    assert admin.role is Role.ADMIN
    assert admin.is_active is False
    assert admin.organisation.plan is None
    assert accounts.list_pending_admins() == [admin]


def test_admin_request_refuses_existing_email(app):
    request_admin()
    with pytest.raises(EmailAlreadyUsed):
        request_admin(organisation="Andere BV")


def test_admin_request_refuses_organisation_name_ignoring_case(app):
    request_admin()
    with pytest.raises(OrganisationNameTaken):
        request_admin(email="ander@acme.nl", organisation="  ACME ")


def test_approve_activates_admin_and_sets_plan(app):
    admin = approved_admin(Plan.FIFTY)
    assert admin.is_active is True
    assert admin.organisation.plan is Plan.FIFTY
    assert accounts.list_pending_admins() == []


def test_approve_unknown_email_fails(app):
    with pytest.raises(UnknownAdmin):
        accounts.approve_admin("niemand@acme.nl", Plan.TEN)


def test_approve_refuses_a_member(app):
    org = make_org("Acme", Plan.TEN)
    make_user(org, "lid@acme.nl", Role.MEMBER, make_team(org))
    with pytest.raises(UnknownAdmin):
        accounts.approve_admin("lid@acme.nl", Plan.TEN)


# --- accounts toevoegen en de limiet ---


def test_admin_adds_member_to_new_team(app):
    admin = approved_admin()
    member = add(admin, "lid@acme.nl", "Innovatie")
    assert member.role is Role.MEMBER
    assert member.team.name == "Innovatie"
    assert member.organisation_id == admin.organisation_id
    assert accounts.authenticate("lid@acme.nl", PASSWORD) is member


def test_team_is_reused_ignoring_case(app):
    admin = approved_admin()
    first = add(admin, "a@acme.nl", "Innovatie")
    second = add(admin, "b@acme.nl", " innovatie ")
    assert first.team_id == second.team_id


def test_admin_without_plan_cannot_add_members(app):
    request_admin()
    admin = accounts.find_user_by_email("beheer@acme.nl")
    with pytest.raises(SeatLimitReached):
        add(admin, "lid@acme.nl")


def test_ten_plan_allows_exactly_ten_members(app):
    admin = approved_admin(Plan.TEN)
    for number in range(10):
        add(admin, f"lid{number}@acme.nl")
    with pytest.raises(SeatLimitReached):
        add(admin, "lid10@acme.nl")
    assert accounts.count_members(admin.organisation) == 10


def test_admins_do_not_count_towards_the_limit(app):
    admin = approved_admin(Plan.TEN)
    assert accounts.count_members(admin.organisation) == 0


def test_deactivated_member_frees_a_seat(app):
    admin = approved_admin(Plan.TEN)
    members = [add(admin, f"lid{number}@acme.nl") for number in range(10)]
    members[0].is_active = False
    db.session.commit()
    add(admin, "nieuw@acme.nl")
    assert accounts.count_members(admin.organisation) == 10


def test_unlimited_plan_has_no_limit(app):
    admin = approved_admin(Plan.UNLIMITED)
    for number in range(60):
        add(admin, f"lid{number}@acme.nl")
    assert accounts.count_members(admin.organisation) == 60


def test_limit_is_per_organisation(app):
    admin_a = approved_admin(Plan.TEN)
    admin_b = approved_admin(Plan.TEN, "beheer@beta.nl", "Beta")
    for number in range(10):
        add(admin_a, f"lid{number}@acme.nl")
    assert add(admin_b, "lid@beta.nl").organisation_id == admin_b.organisation_id


def test_member_cannot_add_members(app):
    admin = approved_admin()
    member = add(admin, "lid@acme.nl")
    with pytest.raises(NotAnAdmin):
        add(member, "ander@acme.nl")


def test_add_member_refuses_existing_email(app):
    admin = approved_admin()
    add(admin, "lid@acme.nl")
    with pytest.raises(EmailAlreadyUsed):
        add(admin, "LID@acme.nl")
    assert db.session.query(User).filter_by(email="lid@acme.nl").count() == 1
