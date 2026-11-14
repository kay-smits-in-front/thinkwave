import os

import pytest
from flask import g
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


def _database_url() -> str:
    # Standaard SQLite in het geheugen; zet TEST_DATABASE_URL om tegen PostgreSQL te testen.
    return normalise_database_url(os.environ.get("TEST_DATABASE_URL", "sqlite://"))


def _app_with(overrides: dict[str, object]):
    app = create_app({"SQLALCHEMY_DATABASE_URI": _database_url(), "TESTING": True, **overrides})

    @app.before_request
    def _forget_user_from_previous_request():
        # De testfixture houdt één app-context open, dus 'g' blijft bestaan tussen aanvragen.
        # In productie krijgt elke aanvraag een nieuwe context; dit bootst dat na.
        g.pop("_login_user", None)

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def app():
    """Gewone testapp: CSRF en rate limiting staan uit, zodat tests niet daarover struikelen."""
    yield from _app_with({"WTF_CSRF_ENABLED": False, "RATELIMIT_ENABLED": False})


@pytest.fixture
def strict_app():
    """Testapp met CSRF en rate limiting aan, om die beveiliging zelf te testen."""
    yield from _app_with({"WTF_CSRF_ENABLED": True, "RATELIMIT_ENABLED": True})


@pytest.fixture
def strict_client(strict_app):
    return strict_app.test_client()


@pytest.fixture
def client(app):
    return app.test_client()
