from flask import Blueprint, jsonify
from sqlalchemy import text

from app.extensions import db

health_blueprint = Blueprint("health", __name__)


@health_blueprint.get("/healthz")
def healthz():
    """Render gebruikt dit om te zien of de app en de database werken."""
    try:
        db.session.execute(text("SELECT 1"))
    except Exception:
        return jsonify(status="database onbereikbaar"), 503
    return jsonify(status="ok")
