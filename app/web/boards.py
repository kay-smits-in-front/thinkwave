from flask import Blueprint, abort, flash, redirect, render_template, url_for
from flask_login import login_required

from app import boards
from app.board_view import build_board_view
from app.boards import (
    ActionAlreadyDone,
    ActionAlreadyStarted,
    ActionNotFound,
    BoardNotFound,
    NotAllowed,
    UnknownComponent,
)
from app.models import Role
from app.web.forms import ComponentForm, EmptyForm
from app.web.helpers import me

boards_blueprint = Blueprint("boards", __name__)


@boards_blueprint.get("/boards/<public_id>")
@login_required
def show_board(public_id: str):
    user = me()
    board = boards.find_visible_board(user, public_id)
    if board is None:
        abort(404)  # Ook voor borden van anderen: er is niets om te verraden.
    return render_template(
        "board.html",
        board=board,
        phases=build_board_view(board),
        can_act=user.role is Role.MEMBER,
        theme=board.edition.value,
    )


@boards_blueprint.post("/boards/<public_id>/start")
@login_required
def start(public_id: str):
    form = ComponentForm()
    if not form.validate_on_submit():
        abort(400)
    try:
        boards.start_action(
            user=me(), board_public_id=public_id, component_key=form.component_key.data
        )
    except BoardNotFound:
        abort(404)
    except NotAllowed:
        abort(403)
    except UnknownComponent:
        abort(400)
    except ActionAlreadyStarted:
        flash("Dit onderdeel is al gestart.", "info")
    return redirect(url_for("boards.show_board", public_id=public_id))


@boards_blueprint.post("/boards/<public_id>/actions/<action_id>/complete")
@login_required
def complete(public_id: str, action_id: str):
    if not EmptyForm().validate_on_submit():
        abort(400)
    try:
        boards.complete_action(user=me(), action_public_id=action_id)
    except ActionNotFound:
        abort(404)
    except NotAllowed:
        abort(403)
    except ActionAlreadyDone:
        flash("Dit onderdeel is al afgerond.", "info")
    return redirect(url_for("boards.show_board", public_id=public_id))
