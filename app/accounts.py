"""Alles rond accounts: inloggen, beheerdersaanvraag, goedkeuren en accounts toevoegen.

Elke functie doet één ding. Deze module weet niets van HTTP; de routes roepen haar aan.
"""

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db
from app.models import Organisation, Plan, Role, Team, User
from app.models.user import normalise_email
from app.scoping import users_visible_to

# Wordt gebruikt zodat inloggen even lang duurt voor onbekende en bekende e-mailadressen.
_DUMMY_PASSWORD_HASH = generate_password_hash("dummy-wachtwoord-voor-timing")


class AccountError(Exception):
    pass


class EmailAlreadyUsed(AccountError):
    pass


class OrganisationNameTaken(AccountError):
    pass


class SeatLimitReached(AccountError):
    pass


class NotAnAdmin(AccountError):
    pass


class UnknownAdmin(AccountError):
    pass


class UnknownUser(AccountError):
    pass


class CannotChangeOwnAccount(AccountError):
    pass


def find_user_by_email(email: str) -> User | None:
    return db.session.scalar(select(User).where(User.email == normalise_email(email)))


def authenticate(email: str, password: str) -> User | None:
    """Geef de gebruiker terug als e-mail en wachtwoord kloppen en het account actief is."""
    user = find_user_by_email(email)
    password_hash = user.password_hash if user else _DUMMY_PASSWORD_HASH
    password_ok = check_password_hash(password_hash, password)
    if user is not None and password_ok and user.is_active:
        return user
    return None


def organisation_name_taken(name: str) -> bool:
    lowered = name.strip().lower()
    found = db.session.scalar(
        select(Organisation.id).where(func.lower(Organisation.name) == lowered)
    )
    return found is not None


def _commit_or_raise(error: type[AccountError]) -> None:
    """Een gelijktijdige dubbele aanmaak wordt door de database tegengehouden."""
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise error() from exc


def request_admin_account(*, email: str, password: str, organisation_name: str) -> User:
    """Maak een beheerdersaccount aan dat nog niet actief is tot het is goedgekeurd."""
    if find_user_by_email(email) is not None:
        raise EmailAlreadyUsed
    if organisation_name_taken(organisation_name):
        raise OrganisationNameTaken

    organisation = Organisation(name=organisation_name.strip())
    admin = User(email=email, role=Role.ADMIN, is_active=False, organisation=organisation)
    admin.set_password(password)
    db.session.add_all([organisation, admin])
    _commit_or_raise(EmailAlreadyUsed)
    return admin


def list_pending_admins() -> list[User]:
    query = select(User).where(User.role == Role.ADMIN, User.is_active.is_(False))
    return list(db.session.scalars(query.order_by(User.id)))


def approve_admin(email: str, plan: Plan) -> User:
    """Activeer een beheerder en zet het abonnement van zijn organisatie."""
    admin = find_user_by_email(email)
    if admin is None or admin.role is not Role.ADMIN:
        raise UnknownAdmin
    admin.is_active = True
    admin.organisation.plan = plan
    db.session.commit()
    return admin


def count_members(organisation: Organisation) -> int:
    """Aantal actieve gewone accounts. Beheerders tellen niet mee voor de limiet."""
    query = select(func.count(User.id)).where(
        User.organisation_id == organisation.id,
        User.role == Role.MEMBER,
        User.is_active.is_(True),
    )
    return db.session.scalar(query) or 0


def has_free_seat(organisation: Organisation) -> bool:
    limit = organisation.seat_limit()
    return limit is None or count_members(organisation) < limit


def _lock_organisation(organisation_id: int) -> Organisation:
    """Blokkeer de organisatie-rij zodat twee beheerders niet tegelijk de limiet passeren."""
    query = select(Organisation).where(Organisation.id == organisation_id).with_for_update()
    return db.session.scalars(query).one()


def get_or_create_team(organisation: Organisation, name: str) -> Team:
    clean_name = name.strip()
    query = select(Team).where(
        Team.organisation_id == organisation.id,
        func.lower(Team.name) == clean_name.lower(),
    )
    team = db.session.scalar(query)
    if team is None:
        team = Team(organisation_id=organisation.id, name=clean_name)
        db.session.add(team)
        db.session.flush()
    return team


def add_member(*, admin: User, email: str, password: str, team_name: str) -> User:
    """Een beheerder voegt een gewoon account toe aan een team, binnen de abonnementslimiet."""
    if admin.role is not Role.ADMIN:
        raise NotAnAdmin
    organisation = _lock_organisation(admin.organisation_id)
    if find_user_by_email(email) is not None:
        db.session.rollback()
        raise EmailAlreadyUsed
    if not has_free_seat(organisation):
        db.session.rollback()
        raise SeatLimitReached

    team = get_or_create_team(organisation, team_name)
    member = User(
        email=email,
        role=Role.MEMBER,
        organisation_id=organisation.id,
        team_id=team.id,
    )
    member.set_password(password)
    db.session.add(member)
    _commit_or_raise(EmailAlreadyUsed)
    return member


def _require_admin(user: User) -> None:
    if user.role is not Role.ADMIN:
        raise NotAnAdmin


def add_admin(*, admin: User, email: str, password: str) -> User:
    """Een beheerder voegt een extra beheerder toe. Beheerders tellen niet mee voor de limiet."""
    _require_admin(admin)
    if find_user_by_email(email) is not None:
        raise EmailAlreadyUsed
    new_admin = User(email=email, role=Role.ADMIN, organisation_id=admin.organisation_id)
    new_admin.set_password(password)
    db.session.add(new_admin)
    _commit_or_raise(EmailAlreadyUsed)
    return new_admin


def list_accounts(admin: User) -> list[User]:
    """Alle accounts van de eigen organisatie, beheerders eerst."""
    _require_admin(admin)
    query = users_visible_to(admin).order_by(User.role, User.id)
    return list(db.session.scalars(query))


def find_user_in_organisation(admin: User, public_id: str) -> User:
    """Zoek een account via de onzichtbare ID, alleen binnen de eigen organisatie."""
    _require_admin(admin)
    target = db.session.scalar(users_visible_to(admin).where(User.public_id == public_id))
    if target is None:
        raise UnknownUser
    return target


def deactivate_user(*, admin: User, public_id: str) -> User:
    target = find_user_in_organisation(admin, public_id)
    if target.id == admin.id:
        raise CannotChangeOwnAccount
    target.is_active = False
    db.session.commit()
    return target


def reactivate_user(*, admin: User, public_id: str) -> User:
    """Zet een account weer aan. Voor een gewoon account moet er een plek vrij zijn."""
    target = find_user_in_organisation(admin, public_id)
    if target.id == admin.id:
        raise CannotChangeOwnAccount
    organisation = _lock_organisation(admin.organisation_id)
    if target.role is Role.MEMBER and not target.is_active and not has_free_seat(organisation):
        db.session.rollback()
        raise SeatLimitReached
    target.is_active = True
    db.session.commit()
    return target
