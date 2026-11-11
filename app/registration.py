"""Zelf registreren: een nieuwe gebruiker krijgt een eigen organisatie en wordt daar beheerder."""

from sqlalchemy import select

from app.extensions import db
from app.models import Organisation, Role, User
from app.models.user import normalise_email


class RegistrationError(ValueError):
    """De registratie kan niet doorgaan. De tekst is bedoeld om aan de gebruiker te tonen."""


def register_owner(organisation_name: str, email: str, password: str) -> User:
    """Maak een organisatie aan met deze gebruiker als beheerder en sla beide op."""
    name = organisation_name.strip()
    if not name:
        raise RegistrationError("Vul een naam voor je organisatie in.")
    if db.session.scalar(select(Organisation).filter_by(name=name)):
        raise RegistrationError("Deze organisatienaam is al in gebruik.")
    if db.session.scalar(select(User).filter_by(email=normalise_email(email))):
        raise RegistrationError("Er bestaat al een account met dit e-mailadres.")

    organisation = Organisation(name=name)
    user = User(email=email, role=Role.ADMIN, organisation=organisation)
    try:
        user.set_password(password)
    except ValueError as error:
        raise RegistrationError(str(error)) from error

    db.session.add_all([organisation, user])
    db.session.commit()
    return user
