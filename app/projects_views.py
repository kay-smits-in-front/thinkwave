"""Projecten en het bord. Gewone formulieren; HTMX (hx-boost) maakt ze vloeiend in de browser."""

from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for
from sqlalchemy import or_, select

from app import board
from app.auth import login_required
from app.extensions import db
from app.models import (
    Action,
    Board,
    ChecklistItem,
    MeasureKind,
    Measurement,
    Note,
    NoteKind,
    Phase,
    Project,
    ProjectAction,
    Role,
)

projects_blueprint = Blueprint("projects", __name__, url_prefix="/projecten")

TABS = ["bord", "logboek", "ideeen", "checklist", "metingen"]


def visible_projects():
    """Beheerders zien alle projecten van hun organisatie, leden die van hun team."""
    query = select(Project).filter_by(organisation_id=g.user.organisation_id)
    if g.user.role is not Role.ADMIN:
        query = query.where(or_(Project.team_id == g.user.team_id, Project.team_id.is_(None)))
    return query.order_by(Project.created_at.desc())


def get_project(project_id: int) -> Project:
    project = db.session.scalar(visible_projects().filter_by(id=project_id))
    if project is None:
        abort(404)
    return project


def form_text(name: str, max_length: int) -> str:
    return request.form.get(name, "").strip()[:max_length]


def form_rating(name: str) -> int | None:
    value = request.form.get(name, "")
    return int(value) if value in {"1", "2", "3", "4", "5"} else None


def back_to(project: Project, tab: str = "bord"):
    return redirect(url_for("projects.show_project", project_id=project.id, tab=tab))


@projects_blueprint.get("")
@login_required
def list_projects():
    projects = db.session.scalars(visible_projects()).all()
    return render_template("projects.html", projects=projects, boards=Board)


@projects_blueprint.post("")
@login_required
def create_project():
    name = form_text("name", 120)
    board_kind = request.form.get("board", Board.WORK)
    if not name or board_kind not in Board:
        flash("Geef het project een naam en kies een bord.")
        return redirect(url_for("projects.list_projects"))
    project = Project(
        name=name,
        goal=form_text("goal", 2000),
        board=Board(board_kind),
        organisation_id=g.user.organisation_id,
        team_id=g.user.team_id,
    )
    db.session.add(project)
    db.session.commit()
    return back_to(project)


@projects_blueprint.get("/<int:project_id>")
@login_required
def show_project(project_id: int):
    project = get_project(project_id)
    tab = request.args.get("tab", "bord")
    if tab not in TABS:
        tab = "bord"
    actions = db.session.scalars(select(Action).order_by(Action.id)).all()
    selected = db.session.get(Action, request.args.get("actie", type=int) or 0)
    impacts = board.phase_impacts(project)
    return render_template(
        "project.html",
        project=project,
        tab=tab,
        phases=list(Phase),
        actions=actions,
        selected=selected,
        impacts=impacts,
        weeks_used=board.weeks_used(project),
        suggestions=board.suggest(project),
        feedback=board.intermission_feedback(project),
        ending=board.ending(project),
        tip=board.tip_for(project),
        uses_left=lambda a: board.uses_left(project, a),
        expected=lambda a: board.expected_impact(a, impacts),
        can_perform=lambda a: board.can_perform(project, a),
        measure_kinds=MeasureKind,
        note_kinds=NoteKind,
    )


@projects_blueprint.post("/<int:project_id>/acties/<int:action_id>")
@login_required
def perform_action(project_id: int, action_id: int):
    project = get_project(project_id)
    action = db.session.get(Action, action_id) or abort(404)
    try:
        step = board.perform(project, action)
    except ValueError as error:
        flash(str(error))
        return back_to(project)
    flash(f"{action.name} uitgevoerd: +{step.impact_percent:g}% {action.phase.value}.")
    return back_to(project)


@projects_blueprint.post("/<int:project_id>/stappen/<int:step_id>")
@login_required
def update_step(project_id: int, step_id: int):
    """Leg vast wat een stap opleverde en hoe goed het ging."""
    project = get_project(project_id)
    step = db.session.get(ProjectAction, step_id)
    if step is None or step.project_id != project.id:
        abort(404)
    step.result = form_text("result", 5000)
    step.self_rating = form_rating("self_rating")
    db.session.commit()
    flash("Stap bijgewerkt.")
    return back_to(project, "logboek")


@projects_blueprint.post("/<int:project_id>/beoordeling")
@login_required
def rate_project(project_id: int):
    project = get_project(project_id)
    project.self_rating = form_rating("self_rating")
    db.session.commit()
    flash("Eindoordeel opgeslagen.")
    return back_to(project, "logboek")


@projects_blueprint.post("/<int:project_id>/notities")
@login_required
def add_note(project_id: int):
    project = get_project(project_id)
    title = form_text("title", 200)
    kind = request.form.get("kind", "")
    if not title or kind not in NoteKind:
        flash("Geef een titel op.")
        return back_to(project, "ideeen")
    db.session.add(Note(project_id=project.id, kind=NoteKind(kind), title=title, body=form_text("body", 20000)))
    db.session.commit()
    return back_to(project, "ideeen")


@projects_blueprint.post("/<int:project_id>/checklist")
@login_required
def add_checklist_item(project_id: int):
    project = get_project(project_id)
    text = form_text("text", 255)
    if text:
        db.session.add(ChecklistItem(project_id=project.id, text=text))
        db.session.commit()
    return back_to(project, "checklist")


@projects_blueprint.post("/<int:project_id>/checklist/<int:item_id>")
@login_required
def toggle_checklist_item(project_id: int, item_id: int):
    project = get_project(project_id)
    item = db.session.get(ChecklistItem, item_id)
    if item is None or item.project_id != project.id:
        abort(404)
    item.done = not item.done
    db.session.commit()
    return back_to(project, "checklist")


@projects_blueprint.post("/<int:project_id>/metingen")
@login_required
def add_measurement(project_id: int):
    project = get_project(project_id)
    kind = request.form.get("kind", "")
    try:
        value = float(request.form.get("value", "").replace(",", "."))
    except ValueError:
        value = None
    if kind not in MeasureKind or value is None:
        flash("Kies wat je meet en vul een getal in.")
        return back_to(project, "metingen")
    db.session.add(
        Measurement(project_id=project.id, kind=MeasureKind(kind), value=value, note=form_text("note", 255))
    )
    db.session.commit()
    return back_to(project, "metingen")
