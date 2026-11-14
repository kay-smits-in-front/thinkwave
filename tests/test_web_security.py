import re

import pytest

from app.extensions import db
from app.scoping import boards_visible_to
from tests.web_helpers import log_in, make_admin, make_board, make_member

CSRF_RE = re.compile(r'name="csrf_token" value="([^"]+)"')


def test_security_headers_on_every_page(app, client):
    for path in ("/login", "/request-admin", "/nergens"):
        headers = client.get(path).headers
        assert "default-src 'none'" in headers["Content-Security-Policy"]
        assert "script-src" not in headers["Content-Security-Policy"]  # dus geen scripts toegestaan
        assert headers["X-Content-Type-Options"] == "nosniff"
        assert headers["X-Frame-Options"] == "DENY"
        assert headers["Referrer-Policy"] == "no-referrer"
        assert headers["Cache-Control"] == "no-store"


def test_static_files_may_be_cached(app, client):
    response = client.get("/static/css/base.css")
    assert response.status_code == 200
    assert response.headers.get("Cache-Control") != "no-store"


def test_no_javascript_and_no_inline_styles_in_pages(app, client):
    admin = make_admin()
    make_member(admin)
    board = make_board(admin)
    log_in(client, "lid@acme.nl")
    for path in ("/dashboard", f"/boards/{board.public_id}", "/login"):
        html = client.get(path).get_data(as_text=True).lower()
        assert "<script" not in html
        assert "style=" not in html
        assert "onclick" not in html


def test_oversized_request_is_refused(app, client):
    response = client.post("/login", data={"email": "a@b.nl", "password": "x" * 20_000})
    assert response.status_code == 413
    assert "Traceback" not in response.get_data(as_text=True)


def test_error_pages_show_no_details(app, client):
    response = client.get("/boards/bestaat-niet")
    assert response.status_code in (302, 404)
    missing = client.get("/helemaal/niets")
    assert missing.status_code == 404
    assert "Niet gevonden." in missing.get_data(as_text=True)


def test_health_endpoint_returns_only_status(app, client):
    assert client.get("/healthz").get_json() == {"status": "ok"}


def test_csrf_blocks_post_without_token(strict_app, strict_client):
    make_member(make_admin())
    response = strict_client.post("/login", data={"email": "lid@acme.nl", "password": "x" * 12})
    assert response.status_code == 400


def test_csrf_allows_post_with_token(strict_app, strict_client):
    make_member(make_admin())
    token = CSRF_RE.search(strict_client.get("/login").get_data(as_text=True)).group(1)
    response = strict_client.post(
        "/login",
        data={"email": "lid@acme.nl", "password": "een-lang-genoeg-wachtwoord", "csrf_token": token},
    )
    assert response.status_code == 302


def test_login_is_rate_limited(strict_app, strict_client):
    token = CSRF_RE.search(strict_client.get("/login").get_data(as_text=True)).group(1)
    statuses = [
        strict_client.post(
            "/login", data={"email": "x@acme.nl", "password": "verkeerd-wachtwoord", "csrf_token": token}
        ).status_code
        for _ in range(12)
    ]
    assert statuses[:10] == [200] * 10
    assert 429 in statuses[10:]


def test_admin_request_is_rate_limited(strict_app, strict_client):
    token = CSRF_RE.search(strict_client.get("/request-admin").get_data(as_text=True)).group(1)
    statuses = [
        strict_client.post(
            "/request-admin",
            data={"email": f"x{n}@acme.nl", "password": "een-lang-genoeg-wachtwoord",
                  "organisation_name": f"Org {n}", "csrf_token": token},
        ).status_code
        for n in range(5)
    ]
    assert statuses.count(429) >= 2


@pytest.mark.parametrize("payload", ["<script>alert(1)</script>", "x' OR '1'='1", "../../etc/passwd", "a‮b"])
def test_names_with_special_characters_are_refused(app, client, payload):
    admin = make_admin()
    log_in(client, "beheer@acme.nl")
    client.post("/admin/boards", data={"team_name": payload, "board_name": "Ok", "edition": "team"})
    client.post("/admin/boards", data={"team_name": "Ok", "board_name": payload, "edition": "team"})
    assert db.session.scalars(boards_visible_to(admin)).first() is None
    html = client.get("/admin/").get_data(as_text=True)
    assert payload not in html and "<script>" not in html


def test_unknown_edition_is_refused(app, client):
    admin = make_admin()
    log_in(client, "beheer@acme.nl")
    client.post("/admin/boards", data={"team_name": "Team", "board_name": "Uniekbord", "edition": "hacker"})
    assert db.session.scalars(boards_visible_to(admin)).first() is None


def test_user_input_is_escaped_in_html(app, client):
    admin = make_admin()
    make_board(admin, team="A&B", name="Q&A")
    log_in(client, "beheer@acme.nl")
    html = client.get("/admin/").get_data(as_text=True)
    assert "A&amp;B" in html and "Q&amp;A" in html
