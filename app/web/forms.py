"""Alle formulieren. Elk veld heeft een lengtegrens en een toegestane vorm.

Namen mogen letters, cijfers, spatie en . & ' - _ bevatten; andere tekens worden geweigerd.
Keuzes (zoals de variant van het bord) komen uit een vaste lijst.
"""

from flask_wtf import FlaskForm
from wtforms import EmailField, PasswordField, SelectField, StringField
from wtforms.fields import SelectChoice
from wtforms.validators import DataRequired, Email, Length, Regexp

from app.models.enums import EDITION_LABELS, Edition
from app.models.user import MAX_PASSWORD_LENGTH, MIN_PASSWORD_LENGTH

NAME_MAX_LENGTH = 80
NAME_PATTERN = r"^[\w .&'-]+$"
NAME_MESSAGE = "Gebruik alleen letters, cijfers, spaties en . & ' - _"


def _strip(value: str | None) -> str | None:
    return value.strip() if isinstance(value, str) else value


def _email_field(label: str = "E-mail") -> EmailField:
    return EmailField(
        label, [DataRequired(), Length(max=254), Email()], filters=[_strip]
    )


def _password_field(label: str = "Wachtwoord") -> PasswordField:
    return PasswordField(
        label, [DataRequired(), Length(min=MIN_PASSWORD_LENGTH, max=MAX_PASSWORD_LENGTH)]
    )


def _name_field(label: str) -> StringField:
    return StringField(
        label,
        [DataRequired(), Length(max=NAME_MAX_LENGTH), Regexp(NAME_PATTERN, message=NAME_MESSAGE)],
        filters=[_strip],
    )


class LoginForm(FlaskForm):
    email = _email_field()
    # Bij inloggen alleen een bovengrens; de minimumlengte geldt bij het aanmaken.
    password = PasswordField("Wachtwoord", [DataRequired(), Length(max=MAX_PASSWORD_LENGTH)])


class AdminRequestForm(FlaskForm):
    email = _email_field()
    password = _password_field(f"Kies een wachtwoord (minimaal {MIN_PASSWORD_LENGTH} tekens)")
    organisation_name = _name_field("Naam van je organisatie")


class AddMemberForm(FlaskForm):
    email = _email_field()
    password = _password_field("Tijdelijk wachtwoord")
    team_name = _name_field("Teamnaam")


class AddAdminForm(FlaskForm):
    email = _email_field()
    password = _password_field("Tijdelijk wachtwoord")


class CreateBoardForm(FlaskForm):
    team_name = _name_field("Teamnaam")
    board_name = _name_field("Naam van het bord")
    edition = SelectField(
        "Variant",
        choices=[SelectChoice(edition.value, EDITION_LABELS[edition]) for edition in Edition],
    )


class RenameTeamForm(FlaskForm):
    name = _name_field("Nieuwe teamnaam")


class ComponentForm(FlaskForm):
    component_key = StringField(
        "Onderdeel", [DataRequired(), Length(max=40), Regexp(r"^[a-z0-9]+$")]
    )


class EmptyForm(FlaskForm):
    """Alleen het CSRF-token; voor knoppen zonder invoer."""
