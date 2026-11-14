from app import accounts
from app.extensions import db
from app.models import Plan
from tests.factories import PASSWORD
from tests.web_helpers import log_in, make_admin, make_member


def test_member_logs_in_and_sees_dashboard(app, client):
    make_member(make_admin())
    response = log_in(client, "LID@acme.nl")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/dashboard")
    assert client.get("/dashboard").status_code == 200


def test_wrong_password_gives_one_generic_message(app, client):
    make_member(make_admin())
    wrong_password = log_in(client, "lid@acme.nl", "verkeerd-wachtwoord")
    unknown_email = log_in(client, "niemand@acme.nl")
    assert b"Inloggen mislukt." in wrong_password.data
    assert b"Inloggen mislukt." in unknown_email.data
    assert wrong_password.status_code == unknown_email.status_code == 200


def test_login_ignores_next_parameter_so_no_open_redirect(app, client):
    make_member(make_admin())
    response = client.post(
        "/login?next=https://evil.example/",
        data={"email": "lid@acme.nl", "password": PASSWORD},
    )
    assert response.headers["Location"] == "/dashboard"


def test_pages_require_login(app, client):
    for path in ("/dashboard", "/admin/", "/admin/accounts", "/boards/abc"):
        response = client.get(path)
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]


def test_logout_ends_the_session(app, client):
    make_member(make_admin())
    log_in(client, "lid@acme.nl")
    client.post("/logout")
    assert client.get("/dashboard").status_code == 302


def test_deactivated_account_loses_access_immediately(app, client):
    admin = make_admin()
    member = make_member(admin)
    log_in(client, "lid@acme.nl")
    assert client.get("/dashboard").status_code == 200
    accounts.deactivate_user(admin=admin, public_id=member.public_id)
    assert client.get("/dashboard").status_code == 302


def test_inactive_account_cannot_log_in(app, client):
    accounts.request_admin_account(email="nieuw@acme.nl", password=PASSWORD, organisation_name="Acme")
    response = log_in(client, "nieuw@acme.nl")
    assert b"Inloggen mislukt." in response.data


def test_admin_request_creates_pending_account(app, client):
    response = client.post(
        "/request-admin",
        data={"email": "x@acme.nl", "password": PASSWORD, "organisation_name": "Acme"},
    )
    assert response.status_code == 302
    assert len(accounts.list_pending_admins()) == 1


def test_admin_request_reveals_nothing_about_existing_accounts(app, client):
    make_admin()
    fresh = client.post(
        "/request-admin",
        data={"email": "x@nieuw.nl", "password": PASSWORD, "organisation_name": "Nieuw"},
        follow_redirects=True,
    )
    taken = client.post(
        "/request-admin",
        data={"email": "beheer@acme.nl", "password": PASSWORD, "organisation_name": "Acme"},
        follow_redirects=True,
    )
    assert fresh.data == taken.data


def test_admin_request_rejects_short_password_and_odd_names(app, client):
    for data in (
        {"email": "x@acme.nl", "password": "kort", "organisation_name": "Acme"},
        {"email": "x@acme.nl", "password": PASSWORD, "organisation_name": "<script>alert(1)</script>"},
        {"email": "geen-email", "password": PASSWORD, "organisation_name": "Acme"},
        {"email": "x@acme.nl", "password": PASSWORD, "organisation_name": "A" * 81},
    ):
        assert client.post("/request-admin", data=data).status_code == 200
    assert accounts.list_pending_admins() == []


def test_member_cannot_open_admin_pages_and_cannot_tell_they_exist(app, client):
    make_member(make_admin())
    log_in(client, "lid@acme.nl")
    for path in ("/admin/", "/admin/accounts"):
        assert client.get(path).status_code == 404
    for path in ("/admin/boards", "/admin/accounts/members", "/admin/accounts/admins"):
        assert client.post(path, data={}).status_code == 404


def test_session_cookie_is_httponly_and_samesite(app, client):
    make_member(make_admin())
    cookie = log_in(client, "lid@acme.nl").headers.get("Set-Cookie", "")
    assert "HttpOnly" in cookie
    assert "SameSite=Lax" in cookie


def test_login_starts_a_fresh_session(app, client):
    make_member(make_admin())
    with client.session_transaction() as session:
        session["planted"] = "x"
    log_in(client, "lid@acme.nl")
    with client.session_transaction() as session:
        assert "planted" not in session


def test_two_clients_in_one_test_are_independent_users(app):
    admin = make_admin()
    make_member(admin)
    admin_client, member_client = app.test_client(), app.test_client()
    log_in(admin_client, "beheer@acme.nl")
    log_in(member_client, "lid@acme.nl")
    assert admin_client.get("/admin/").status_code == 200
    assert member_client.get("/admin/").status_code == 404
    assert admin_client.get("/admin/").status_code == 200
