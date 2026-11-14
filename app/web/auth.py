from flask import Blueprint, flash, redirect, render_template, session, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import select

from app import accounts
from app.accounts import EmailAlreadyUsed, OrganisationNameTaken
from app.extensions import db, limiter, login_manager
from app.models import User
from app.web.forms import AdminRequestForm, EmptyForm, LoginForm

auth_blueprint = Blueprint("auth", __name__)

login_manager.login_view = "auth.login"
login_manager.login_message = "Log eerst in."
login_manager.session_protection = "strong"


@login_manager.user_loader
def load_user(public_id: str) -> User | None:
    """Elke aanvraag opnieuw: een gedeactiveerd account verliest direct zijn toegang."""
    user = db.session.scalar(select(User).where(User.public_id == public_id))
    return user if user is not None and user.is_active else None


@auth_blueprint.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute;60 per hour", methods=["POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    form = LoginForm()
    if form.validate_on_submit():
        user = accounts.authenticate(form.email.data, form.password.data)
        if user is not None:
            session.clear()  # Een nieuwe sessie na inloggen voorkomt 'session fixation'.
            session.permanent = True
            login_user(user)
            return redirect(url_for("main.dashboard"))  # Bewust geen 'next': geen open redirect.
        flash("Inloggen mislukt.", "error")
    return render_template("login.html", form=form)


@auth_blueprint.route("/request-admin", methods=["GET", "POST"])
@limiter.limit("3 per hour", methods=["POST"])
def request_admin():
    form = AdminRequestForm()
    if form.validate_on_submit():
        try:
            accounts.request_admin_account(
                email=form.email.data,
                password=form.password.data,
                organisation_name=form.organisation_name.data,
            )
        except (EmailAlreadyUsed, OrganisationNameTaken):
            pass  # Zelfde antwoord als bij succes, zodat niemand kan uitproberen wat al bestaat.
        flash("Aanvraag ontvangen. Je hoort het zodra je account is goedgekeurd.", "info")
        return redirect(url_for("auth.login"))
    return render_template("request_admin.html", form=form)


@auth_blueprint.post("/logout")
@login_required
def logout():
    if EmptyForm().validate_on_submit():
        logout_user()
        session.clear()
    return redirect(url_for("auth.login"))
