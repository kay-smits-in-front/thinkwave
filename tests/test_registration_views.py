from sqlalchemy import select

from app.extensions import db
from app.models import User

PASSWORD = "een-lang-genoeg-wachtwoord"


def post_form(client, **overrides):
    data = {"organisation_name": "Acme", "email": "kay@example.com", "password": PASSWORD}
    data.update(overrides)
    return client.post("/registreren", data=data)


def test_form_is_shown(client):
    response = client.get("/registreren")
    assert response.status_code == 200
    assert 'name="organisation_name"' in response.text
    assert 'name="password"' in response.text


def test_valid_form_creates_account_and_redirects(client):
    response = post_form(client)
    assert response.status_code == 302
    assert db.session.scalar(select(User).filter_by(email="kay@example.com")) is not None


def test_success_message_is_shown_after_redirect(client):
    response = client.post(
        "/registreren",
        data={"organisation_name": "Acme", "email": "kay@example.com", "password": PASSWORD},
        follow_redirects=True,
    )
    assert "Je account is aangemaakt." in response.text


def test_invalid_form_shows_error_and_keeps_input_but_not_password(client):
    response = post_form(client, password="te-kort")
    assert response.status_code == 400
    assert "Wachtwoord moet minimaal 12 tekens hebben." in response.text
    assert 'value="kay@example.com"' in response.text
    assert "te-kort" not in response.text
