"""Beheer: een beheerder maakt accounts aan voor de eigen organisatie."""

from flask import Blueprint, flash, g, redirect, render_template, request, url_for
from sqlalchemy import func, select

from app import board
from app.auth import admin_required
from app.extensions import db
from app.models import Role, Team, User
from app.registration import RegistrationError
from app.models.user import normalise_email

admin_blueprint = Blueprint("admin", __name__, url_prefix="/beheer")


def member_count(organisation_id: int) -> int:
    query = select(func.count()).select_from(User).filter_by(organisation_id=organisation_id, role=Role.MEMBER)
    return db.session.scalar(query)


def get_or_create_team(organisation_id: int, name: str) -> Team:
    team = db.session.scalar(select(Team).filter_by(organisation_id=organisation_id, name=name))
    if team is None:
        team = Team(organisation_id=organisation_id, name=name)
        db.session.add(team)
        db.session.flush()
    return team


def add_member(email: str, password: str, team_name: str) -> User:
    """Maak een gewoon account in de organisatie van de beheerder, binnen de limiet van het abonnement."""
    organisation = g.user.organisation
    limit = organisation.seat_limit()
    if limit is not None and member_count(organisation.id) >= limit:
        raise RegistrationError(f"Je abonnement staat {limit} accounts toe.")
    if not team_name:
        raise RegistrationError("Vul een team in.")
    if db.session.scalar(select(User).filter_by(email=normalise_email(email))):
        raise RegistrationError("Er bestaat al een account met dit e-mailadres.")
    team = get_or_create_team(organisation.id, team_name)
    user = User(email=email, role=Role.MEMBER, organisation_id=organisation.id, team_id=team.id)
    try:
        user.set_password(password)
    except ValueError as error:
        raise RegistrationError(str(error)) from error
    db.session.add(user)
    db.session.commit()
    return user


@admin_blueprint.get("/accounts")
@admin_required
def list_accounts():
    users = db.session.scalars(
        select(User).filter_by(organisation_id=g.user.organisation_id).order_by(User.email)
    ).all()
    return render_template("accounts.html", users=users, error=None, form={})


@admin_blueprint.post("/accounts")
@admin_required
def create_account():
    form = {"email": request.form.get("email", ""), "team": request.form.get("team", "").strip()[:120]}
    try:
        add_member(form["email"], request.form.get("password", ""), form["team"])
    except RegistrationError as error:
        db.session.rollback()
        users = db.session.scalars(select(User).filter_by(organisation_id=g.user.organisation_id)).all()
        return render_template("accounts.html", users=users, error=str(error), form=form), 400
    flash(f"Account voor {form['email']} aangemaakt.")
    return redirect(url_for("admin.list_accounts"))


def editing_defaults() -> bool:
    """De platform-admin kan met ?standaard=1 de standaardset voor iedereen wijzigen."""
    return g.user.is_platform_admin and request.values.get("standaard") == "1"


@admin_blueprint.get("/taken")
@admin_required
def list_tasks():
    defaults = editing_defaults()
    actions = board.default_actions() if defaults else board.organisation_actions(g.user.organisation_id)
    return render_template("tasks.html", actions=actions, defaults=defaults, max_weeks=board.MAX_WEEKS)


@admin_blueprint.post("/taken/<int:action_id>")
@admin_required
def update_task(action_id: int):
    """Titel, beschrijving en standaardduur van een taak wijzigen voor de eigen organisatie."""
    defaults = editing_defaults()
    allowed = board.default_actions() if defaults else board.organisation_actions(g.user.organisation_id)
    action = next((a for a in allowed if a.id == action_id), None)
    name = request.form.get("name", "").strip()[:120]
    weeks = request.form.get("duration_weeks", "")
    if action is None or not name or not weeks.isdigit() or not 1 <= int(weeks) <= board.MAX_WEEKS:
        flash("Vul een titel en een duur van 1 tot 104 weken in.")
        return redirect(url_for("admin.list_tasks", standaard="1" if defaults else None))
    target = action if defaults else board.editable_copy(action, g.user.organisation_id)
    target.name = name
    target.description = request.form.get("description", "").strip()[:5000]
    target.duration_weeks = int(weeks)
    db.session.commit()
    flash(f"{name} opgeslagen.")
    return redirect(url_for("admin.list_tasks", standaard="1" if defaults else None) + f"#taak-{target.base_id}")
