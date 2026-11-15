"""Inloggen, uitloggen en de ingelogde gebruiker. Sessie-cookie van Flask, geen extra library."""

from collections.abc import Callable
from functools import wraps

from flask import Blueprint, abort, g, redirect, render_template, request, session, url_for
from sqlalchemy import select

from app.extensions import db
from app.models import User
from app.models.user import normalise_email

auth_blueprint = Blueprint("auth", __name__)


def log_in(user: User) -> None:
    session.clear()  # nieuwe sessie na inloggen tegen session fixation
    session["user_id"] = user.id


def load_current_user() -> None:
    """Zet de ingelogde gebruiker op g.user (of None). Draait voor elk verzoek."""
    user_id = session.get("user_id")
    user = db.session.get(User, user_id) if user_id else None
    g.user = user if user and user.is_active else None


def login_required(view: Callable) -> Callable:
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            return redirect(url_for("auth.show_login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def admin_required(view: Callable) -> Callable:
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not g.user.is_manager:
            abort(403)
        return view(*args, **kwargs)

    return wrapped


def find_user(email: str, password: str) -> User | None:
    """De actieve gebruiker bij deze gegevens, of None."""
    user = db.session.scalar(select(User).filter_by(email=normalise_email(email)))
    if user and user.is_active and user.check_password(password):
        return user
    return None


def safe_next(target: str | None) -> str:
    """Alleen doorsturen naar een pad op deze site, nooit naar een andere website."""
    if target and target.startswith("/") and not target.startswith("//"):
        return target
    return url_for("projects.list_projects")


@auth_blueprint.get("/")
def home():
    return redirect(url_for("projects.list_projects" if g.user else "auth.show_login"))


@auth_blueprint.get("/inloggen")
def show_login():
    return render_template("login.html", email="", error=None)


@auth_blueprint.post("/inloggen")
def submit_login():
    email = request.form.get("email", "")
    user = find_user(email, request.form.get("password", ""))
    if user is None:
        error = "E-mailadres of wachtwoord klopt niet."
        return render_template("login.html", email=email, error=error), 400
    log_in(user)
    return redirect(safe_next(request.args.get("next")))


@auth_blueprint.post("/uitloggen")
def log_out():
    session.clear()
    return redirect(url_for("auth.show_login"))
