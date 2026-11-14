from flask import Blueprint, abort, flash, redirect, render_template, url_for

from app import accounts, boards
from app.accounts import (
    CannotChangeOwnAccount,
    EmailAlreadyUsed,
    SeatLimitReached,
    UnknownUser,
)
from app.boards import BoardNameTaken, TeamNameTaken, TeamNotFound
from app.models import Edition
from app.overview import team_overviews
from app.web.forms import (
    AddAdminForm,
    AddMemberForm,
    CreateBoardForm,
    EmptyForm,
    RenameTeamForm,
)
from app.web.helpers import admin_required, me

admin_blueprint = Blueprint("admin", __name__, url_prefix="/admin")


def _flash_form_errors(form) -> None:
    for errors in form.errors.values():
        for error in errors:
            flash(error, "error")


@admin_blueprint.get("/")
@admin_required
def overview():
    return render_template(
        "admin_overview.html",
        teams=team_overviews(me()),
        board_form=CreateBoardForm(),
        rename_form=RenameTeamForm(),
    )


@admin_blueprint.post("/boards")
@admin_required
def create_board():
    form = CreateBoardForm()
    if form.validate_on_submit():
        try:
            boards.create_board(
                admin=me(),
                team_name=form.team_name.data,
                board_name=form.board_name.data,
                edition=Edition(form.edition.data),
            )
            flash("Bord aangemaakt.", "info")
        except BoardNameTaken:
            flash("Dit team heeft al een bord met deze naam.", "error")
    else:
        _flash_form_errors(form)
    return redirect(url_for("admin.overview"))


@admin_blueprint.post("/teams/<public_id>/rename")
@admin_required
def rename_team(public_id: str):
    form = RenameTeamForm()
    if form.validate_on_submit():
        try:
            boards.rename_team(admin=me(), team_public_id=public_id, new_name=form.name.data)
            flash("Teamnaam aangepast.", "info")
        except TeamNotFound:
            abort(404)
        except TeamNameTaken:
            flash("Er bestaat al een team met deze naam.", "error")
    else:
        _flash_form_errors(form)
    return redirect(url_for("admin.overview"))


@admin_blueprint.get("/accounts")
@admin_required
def accounts_page():
    admin = me()
    organisation = admin.organisation
    return render_template(
        "admin_accounts.html",
        users=accounts.list_accounts(admin),
        me_public_id=admin.public_id,
        member_count=accounts.count_members(organisation),
        seat_limit=organisation.seat_limit(),
        member_form=AddMemberForm(),
        admin_form=AddAdminForm(),
        empty_form=EmptyForm(),
    )


@admin_blueprint.post("/accounts/members")
@admin_required
def add_member():
    form = AddMemberForm()
    if form.validate_on_submit():
        try:
            accounts.add_member(
                admin=me(),
                email=form.email.data,
                password=form.password.data,
                team_name=form.team_name.data,
            )
            flash("Account toegevoegd.", "info")
        except EmailAlreadyUsed:
            flash("Dit e-mailadres kan niet gebruikt worden.", "error")
        except SeatLimitReached:
            flash("Het maximum aantal accounts van je abonnement is bereikt.", "error")
    else:
        _flash_form_errors(form)
    return redirect(url_for("admin.accounts_page"))


@admin_blueprint.post("/accounts/admins")
@admin_required
def add_admin():
    form = AddAdminForm()
    if form.validate_on_submit():
        try:
            accounts.add_admin(admin=me(), email=form.email.data, password=form.password.data)
            flash("Beheerder toegevoegd.", "info")
        except EmailAlreadyUsed:
            flash("Dit e-mailadres kan niet gebruikt worden.", "error")
    else:
        _flash_form_errors(form)
    return redirect(url_for("admin.accounts_page"))


@admin_blueprint.post("/accounts/<public_id>/deactivate")
@admin_required
def deactivate(public_id: str):
    if not EmptyForm().validate_on_submit():
        abort(400)
    try:
        accounts.deactivate_user(admin=me(), public_id=public_id)
        flash("Account uitgezet.", "info")
    except UnknownUser:
        abort(404)
    except CannotChangeOwnAccount:
        flash("Je kunt je eigen account niet uitzetten.", "error")
    return redirect(url_for("admin.accounts_page"))


@admin_blueprint.post("/accounts/<public_id>/reactivate")
@admin_required
def reactivate(public_id: str):
    if not EmptyForm().validate_on_submit():
        abort(400)
    try:
        accounts.reactivate_user(admin=me(), public_id=public_id)
        flash("Account weer aangezet.", "info")
    except UnknownUser:
        abort(404)
    except CannotChangeOwnAccount:
        flash("Dit kan niet voor je eigen account.", "error")
    except SeatLimitReached:
        flash("Het maximum aantal accounts van je abonnement is bereikt.", "error")
    return redirect(url_for("admin.accounts_page"))
