import pytest

from app.config import build_config, normalise_database_url

GOOD_PRODUCTION = {
    "APP_ENV": "production",
    "SECRET_KEY": "x" * 40,
    "DATABASE_URL": "postgres://user:pw@host/db",
    "TRUSTED_HOSTS": "thinkwave.example",
}


def test_postgres_url_uses_psycopg_driver():
    assert normalise_database_url("postgres://u:p@h/d") == "postgresql+psycopg://u:p@h/d"
    assert normalise_database_url("postgresql://u:p@h/d") == "postgresql+psycopg://u:p@h/d"


def test_development_works_without_settings():
    config = build_config({})
    assert config["SESSION_COOKIE_SECURE"] is False


def test_production_with_good_settings_is_secure():
    config = build_config(GOOD_PRODUCTION)
    assert config["SESSION_COOKIE_SECURE"] is True
    assert config["SQLALCHEMY_DATABASE_URI"].startswith("postgresql+psycopg://")


@pytest.mark.parametrize("missing", ["SECRET_KEY", "DATABASE_URL", "TRUSTED_HOSTS"])
def test_production_refuses_to_start_without_setting(missing):
    environ = {k: v for k, v in GOOD_PRODUCTION.items() if k != missing}
    with pytest.raises(RuntimeError, match=missing):
        build_config(environ)


def test_production_refuses_sqlite():
    environ = {**GOOD_PRODUCTION, "DATABASE_URL": "sqlite:///x.db"}
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        build_config(environ)
