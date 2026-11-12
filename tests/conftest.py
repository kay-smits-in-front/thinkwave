import os

import pytest
from sqlalchemy import event
from sqlalchemy.engine import Engine

from app import create_app
from app.config import normalise_database_url
from app.extensions import db


@event.listens_for(Engine, "connect")
def _enforce_sqlite_foreign_keys(dbapi_connection, _record):
    """SQLite controleert foreign keys standaard niet; PostgreSQL wel."""
    if dbapi_connection.__class__.__module__.startswith("sqlite3"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


@pytest.fixture
def app():
    # Standaard SQLite in het geheugen; zet TEST_DATABASE_URL om tegen PostgreSQL te testen.
    database_url = normalise_database_url(os.environ.get("TEST_DATABASE_URL", "sqlite://"))
    app = create_app({"SQLALCHEMY_DATABASE_URI": database_url, "TESTING": True})
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def seeded(app):
    from app.board import seed_actions

    seed_actions()
    return app


def csrf_post(client, url, data=None, **kwargs):
    """POST met een geldig CSRF-token, zoals een formulier uit de app dat doet."""
    with client.session_transaction() as session:
        session.setdefault("csrf_token", "test-token")
        token = session["csrf_token"]
    return client.post(url, data={**(data or {}), "csrf_token": token}, **kwargs)
