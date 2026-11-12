from sqlalchemy import select

from app.extensions import db
from app.models import Action, Measurement, Note, Project, User
from tests.conftest import csrf_post

PASSWORD = "een-lang-genoeg-wachtwoord"


def register(client, org="Acme", email="kay@example.com"):
    csrf_post(client, "/registreren", {"organisation_name": org, "email": email, "password": PASSWORD})


def create_project(client, name="Nieuwe app", board="youth") -> Project:
    csrf_post(client, "/projecten", {"name": name, "goal": "Iets nieuws", "board": board})
    return db.session.scalar(select(Project).filter_by(name=name))


def test_pages_require_login(client):
    response = client.get("/projecten")
    assert response.status_code == 302
    assert "/inloggen" in response.headers["Location"]


def test_login_and_logout(client):
    register(client)
    csrf_post(client, "/uitloggen")
    assert client.get("/projecten").status_code == 302
    response = csrf_post(client, "/inloggen", {"email": "KAY@example.com", "password": PASSWORD})
    assert response.status_code == 302
    assert client.get("/projecten").status_code == 200


def test_wrong_password_is_refused(client):
    register(client)
    csrf_post(client, "/uitloggen")
    response = csrf_post(client, "/inloggen", {"email": "kay@example.com", "password": "verkeerd-wachtwoord"})
    assert response.status_code == 400
    assert "klopt niet" in response.text


def test_login_never_redirects_to_another_site(client):
    register(client)
    csrf_post(client, "/uitloggen")
    response = csrf_post(client, "/inloggen?next=//evil.example", {"email": "kay@example.com", "password": PASSWORD})
    assert response.headers["Location"].endswith("/projecten")


def test_full_board_flow(client, seeded):
    register(client)
    project = create_project(client)
    page = client.get(f"/projecten/{project.id}")
    assert page.status_code == 200
    assert 'data-board="youth"' in page.text

    talk = db.session.scalar(select(Action).filter_by(name="Talk to Customer"))
    assert "Talk to Customer" in client.get(f"/projecten/{project.id}?actie={talk.id}").text
    csrf_post(client, f"/projecten/{project.id}/acties/{talk.id}")
    db.session.refresh(project)
    step = project.steps[0]
    assert step.impact_percent == 10.0

    csrf_post(client, f"/projecten/{project.id}/stappen/{step.id}", {"result": "5 klanten gesproken", "self_rating": "4"})
    csrf_post(client, f"/projecten/{project.id}/notities", {"kind": "idea", "title": "App voor scholen"})
    csrf_post(client, f"/projecten/{project.id}/checklist", {"text": "Interviewvragen maken"})
    csrf_post(client, f"/projecten/{project.id}/metingen", {"kind": "budget", "value": "1500,50"})
    db.session.expire_all()

    assert step.self_rating == 4
    assert db.session.scalar(select(Note)).title == "App voor scholen"
    assert db.session.scalar(select(Measurement)).value == 1500.5
    for tab in ("logboek", "ideeen", "checklist", "metingen"):
        assert client.get(f"/projecten/{project.id}?tab={tab}").status_code == 200


def test_other_organisation_cannot_see_project(client, seeded):
    register(client)
    project = create_project(client)
    csrf_post(client, "/uitloggen")
    register(client, org="Beta", email="b@example.com")
    assert client.get(f"/projecten/{project.id}").status_code == 404


def test_admin_adds_member_who_sees_team_projects(client, seeded):
    register(client)
    response = csrf_post(client, "/beheer/accounts", {"email": "lid@example.com", "team": "Innovatie", "password": PASSWORD})
    assert response.status_code == 302
    member = db.session.scalar(select(User).filter_by(email="lid@example.com"))
    assert member.team.name == "Innovatie"

    csrf_post(client, "/uitloggen")
    csrf_post(client, "/inloggen", {"email": "lid@example.com", "password": PASSWORD})
    assert client.get("/beheer/accounts").status_code == 403
    assert client.get("/projecten").status_code == 200
