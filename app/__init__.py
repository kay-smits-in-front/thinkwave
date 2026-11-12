import os
from collections.abc import Mapping

from flask import Flask

from app.config import build_config
from app.extensions import db, migrate


def create_app(overrides: Mapping[str, object] | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_mapping(build_config(os.environ))
    if overrides:
        app.config.from_mapping(overrides)

    db.init_app(app)
    from app import models  # noqa: F401  (registreert de modellen bij SQLAlchemy)

    migrate.init_app(app, db)

    from app.admin_views import admin_blueprint
    from app.auth import auth_blueprint, load_current_user
    from app.board import seed_actions
    from app.csrf import check_csrf, csrf_token
    from app.health import health_blueprint
    from app.projects_views import projects_blueprint
    from app.registration_views import registration_blueprint

    app.before_request(load_current_user)
    app.before_request(check_csrf)
    app.jinja_env.globals["csrf_token"] = csrf_token

    for blueprint in (health_blueprint, auth_blueprint, registration_blueprint, projects_blueprint, admin_blueprint):
        app.register_blueprint(blueprint)

    @app.cli.command("seed")
    def seed_command() -> None:
        """Zet de actiecatalogus van het bord in de database."""
        print(f"{seed_actions()} acties bijgewerkt.")

    return app
