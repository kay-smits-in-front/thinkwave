import os
from collections.abc import Mapping

from flask import Flask

from app.config import build_config
from app.extensions import db, migrate
from app.health import health_blueprint


def create_app(overrides: Mapping[str, object] | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_mapping(build_config(os.environ))
    if overrides:
        app.config.from_mapping(overrides)

    db.init_app(app)
    from app import models  # noqa: F401  (registreert de modellen bij SQLAlchemy)

    migrate.init_app(app, db)

    app.register_blueprint(health_blueprint)
    return app
