from flask import Blueprint, redirect, render_template, url_for
from flask_login import current_user, login_required
from sqlalchemy import select

from app.extensions import db
from app.models import Board, Role
from app.scoping import boards_visible_to
from app.web.helpers import me

main_blueprint = Blueprint("main", __name__)


@main_blueprint.get("/")
def index():
    target = "main.dashboard" if current_user.is_authenticated else "auth.login"
    return redirect(url_for(target))


@main_blueprint.get("/dashboard")
@login_required
def dashboard():
    user = me()
    if user.role is Role.ADMIN:
        return redirect(url_for("admin.overview"))
    boards = db.session.scalars(boards_visible_to(user).order_by(Board.name))
    return render_template("dashboard.html", team=user.team, boards=list(boards))
