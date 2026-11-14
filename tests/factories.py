"""Hulpfuncties om testdata aan te maken."""

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


def make_user(
    org: Organisation,
    email: str,
    role: Role,
    team: Team | None = None,
    *,
    is_active: bool = True,
) -> User:
    user = User(
        email=email,
        role=role,
        organisation_id=org.id,
        team_id=team.id if team else None,
        is_active=is_active,
    )
    user.set_password(PASSWORD)
    db.session.add(user)
    db.session.flush()
    return user
