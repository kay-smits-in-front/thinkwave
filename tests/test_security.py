from sqlalchemy import select

from app.extensions import db
from app.models import Measurement, Project
from tests.conftest import csrf_post

PASSWORD = "een-lang-genoeg-wachtwoord"


def register(client, org="Acme", email="kay@example.com"):
    return csrf_post(client, "/registreren", {"organisation_name": org, "email": email, "password": PASSWORD})


def test_security_headers_on_every_page(client):
    headers = client.get("/inloggen").headers
    assert "frame-ancestors 'none'" in headers["Content-Security-Policy"]
    assert "script-src 'self' https://unpkg.com" in headers["Content-Security-Policy"]
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "DENY"


def test_logged_in_pages_are_not_cached(client):
    register(client)
    assert client.get("/projecten").headers["Cache-Control"] == "no-store"


def test_password_guessing_is_rate_limited_per_account(client):
    codes = [csrf_post(client, "/inloggen", {"email": "x@example.com", "password": "fout-wachtwoord-1"}).status_code for _ in range(11)]
    assert codes[:10] == [400] * 10
    assert codes[10] == 429
    # Een klasgenoot achter hetzelfde IP-adres kan gewoon verder.
    assert csrf_post(client, "/inloggen", {"email": "y@example.com", "password": "fout-wachtwoord-1"}).status_code == 400


def test_registration_is_rate_limited(client):
    codes = [register(client, org=f"Org {i}", email=f"u{i}@example.com").status_code for i in range(21)]
    assert codes[-1] == 429


def test_large_request_is_refused(client):
    response = csrf_post(client, "/inloggen", {"email": "a" * 70_000, "password": "x"})
    assert response.status_code == 413


def test_error_pages_show_no_technical_details(client):
    response = client.get("/bestaat-niet")
    assert response.status_code == 404
    assert "Traceback" not in response.text and "werkzeug" not in response.text.lower()


def test_backslash_redirect_is_not_followed(client):
    register(client)
    csrf_post(client, "/uitloggen")
    response = csrf_post(client, "/inloggen?next=/\\\\evil.example", {"email": "kay@example.com", "password": PASSWORD})
    assert response.headers["Location"].endswith("/projecten")


def test_measurement_rejects_nan_infinity_and_huge_numbers(client, seeded):
    register(client)
    csrf_post(client, "/projecten", {"name": "P", "board": "work"})
    project = db.session.scalar(select(Project))
    for bad in ("nan", "inf", "-inf", "1e308", "1e10", "12abc", ""):
        csrf_post(client, f"/projecten/{project.id}/metingen", {"kind": "budget", "value": bad})
    csrf_post(client, f"/projecten/{project.id}/metingen", {"kind": "budget", "value": "2500"})
    assert [m.value for m in db.session.scalars(select(Measurement))] == [2500.0]


def test_unknown_enum_values_are_refused(client, seeded):
    register(client)
    csrf_post(client, "/projecten", {"name": "P", "board": "hacker"})
    assert db.session.scalar(select(Project)) is None


def test_sql_injection_in_login_is_harmless(client):
    register(client)
    csrf_post(client, "/uitloggen")
    response = csrf_post(client, "/inloggen", {"email": "' OR '1'='1", "password": "' OR '1'='1"})
    assert response.status_code == 400
    assert client.get("/projecten").status_code == 302


def test_script_in_input_is_escaped(client, seeded):
    register(client)
    csrf_post(client, "/projecten", {"name": "<script>alert(1)</script>", "board": "work"})
    page = client.get("/projecten").text
    assert "<script>alert(1)</script>" not in page
    assert "&lt;script&gt;" in page


def test_checklist_has_a_ceiling_per_project(client, seeded, monkeypatch):
    from app import projects_views

    monkeypatch.setattr(projects_views, "MAX_ITEMS_PER_PROJECT", 2)
    register(client)
    csrf_post(client, "/projecten", {"name": "P", "board": "work"})
    project = db.session.scalar(select(Project))
    for i in range(4):
        csrf_post(client, f"/projecten/{project.id}/checklist", {"text": f"punt {i}"})
    db.session.refresh(project)
    assert len(project.checklist) == 2


def test_non_ascii_csrf_token_is_a_clean_400(client):
    with client.session_transaction() as session:
        session["csrf_token"] = "abc"
    assert client.post("/inloggen", data={"csrf_token": "ééé"}).status_code == 400
