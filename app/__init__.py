import os
from collections.abc import Mapping

from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

from app.cli import register_commands
from app.config import build_config
from app.extensions import csrf, db, limiter, login_manager, migrate
from app.formatting import mask_email
from app.health import health_blueprint
from app.models.enums import EDITION_LABELS
from app.web.admin import admin_blueprint
from app.web.auth import auth_blueprint
from app.web.boards import boards_blueprint
from app.web.main import main_blueprint
from app.web.security import register_security


def create_app(overrides: Mapping[str, object] | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_mapping(build_config(os.environ))
    if overrides:
        app.config.from_mapping(overrides)

    hops = app.config["TRUSTED_PROXY_HOPS"]
    if hops:  # Achter Render: vertrouw precies dit aantal proxy's voor het IP-adres.
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=hops, x_proto=hops, x_host=hops)

    db.init_app(app)
    from app import models  # noqa: F401  (registreert de modellen bij SQLAlchemy)

    migrate.init_app(app, db)
    csrf.init_app(app)
    limiter.init_app(app)
    login_manager.init_app(app)

    app.jinja_env.filters["mask_email"] = mask_email
    app.jinja_env.globals["EDITION_LABELS"] = {e.value: label for e, label in EDITION_LABELS.items()}

    for blueprint in (
        health_blueprint,
        main_blueprint,
        auth_blueprint,
        boards_blueprint,
        admin_blueprint,
    ):
        app.register_blueprint(blueprint)

    register_security(app)
    register_commands(app)
    return app
