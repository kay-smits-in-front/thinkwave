import pytest

from app.models import Role
from app.registration import RegistrationError, register_owner

PASSWORD = "een-lang-genoeg-wachtwoord"


def test_registration_creates_organisation_with_admin(app):
    user = register_owner("  Acme  ", "Kay@Example.com", PASSWORD)
    assert user.id is not None
    assert user.role is Role.ADMIN
    assert user.team_id is None
    assert user.organisation.name == "Acme"
    assert user.check_password(PASSWORD)


def test_new_organisation_has_no_plan_yet(app):
    user = register_owner("Acme", "a@example.com", PASSWORD)
    assert user.organisation.plan is None


@pytest.mark.parametrize(
    ("name", "email", "password", "message"),
    [
        ("   ", "b@example.com", PASSWORD, "naam"),
        ("Acme", "b@example.com", PASSWORD, "organisatienaam"),
        ("Beta", " A@EXAMPLE.com ", PASSWORD, "e-mailadres"),
        ("Beta", "b@example.com", "kort", "Wachtwoord"),
    ],
)
def test_registration_is_refused(app, name, email, password, message):
    register_owner("Acme", "a@example.com", PASSWORD)
    with pytest.raises(RegistrationError, match=message):
        register_owner(name, email, password)
