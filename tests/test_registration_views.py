from sqlalchemy import select

from app.extensions import db
from app.models import User
from tests.conftest import csrf_post

PASSWORD = "een-lang-genoeg-wachtwoord"


def post_form(client, **overrides):
    data = {"organisation_name": "Acme", "email": "kay@example.com", "password": PASSWORD}
    data.update(overrides)
    return csrf_post(client, "/registreren", data)


def test_form_is_shown(client):
    response = client.get("/registreren")
    assert response.status_code == 200
    assert 'name="organisation_name"' in response.text
    assert 'name="password"' in response.text


def test_valid_form_creates_account_and_redirects(client):
    response = post_form(client)
    assert response.status_code == 302
    assert db.session.scalar(select(User).filter_by(email="kay@example.com")) is not None


def test_registration_logs_in_and_opens_projects(client):
    response = post_form(client)
    assert response.headers["Location"].endswith("/projecten")
    assert client.get("/projecten").status_code == 200


def test_post_without_csrf_token_is_refused(client):
    response = client.post("/registreren", data={"organisation_name": "Acme"})
    assert response.status_code == 400


def test_invalid_form_shows_error_and_keeps_input_but_not_password(client):
    response = post_form(client, password="te-kort")
    assert response.status_code == 400
    assert "Wachtwoord moet minimaal 12 tekens hebben." in response.text
    assert 'value="kay@example.com"' in response.text
    assert "te-kort" not in response.text
