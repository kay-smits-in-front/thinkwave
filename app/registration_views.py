"""Pagina waarop een nieuwe gebruiker zelf een account en organisatie aanmaakt."""

from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.registration import RegistrationError, register_owner

registration_blueprint = Blueprint("registration", __name__)


@registration_blueprint.get("/registreren")
def show_registration_form():
    """Toon het lege registratieformulier."""
    return render_template("registration.html", form={}, error=None)


@registration_blueprint.post("/registreren")
def submit_registration():
    """Verwerk het formulier; bij een fout blijft de ingevulde tekst staan (behalve het wachtwoord)."""
    form = {
        "organisation_name": request.form.get("organisation_name", ""),
        "email": request.form.get("email", ""),
    }
    try:
        register_owner(form["organisation_name"], form["email"], request.form.get("password", ""))
    except RegistrationError as error:
        return render_template("registration.html", form=form, error=str(error)), 400

    flash("Je account is aangemaakt.")
    return redirect(url_for("registration.show_registration_form"))
