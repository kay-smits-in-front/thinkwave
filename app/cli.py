"""Beheer via de server: alleen wie toegang heeft tot de server kan een beheerder goedkeuren."""

import click
from flask import Flask

from app import accounts
from app.accounts import UnknownAdmin
from app.formatting import mask_email
from app.models import Plan


def register_commands(app: Flask) -> None:
    @app.cli.command("pending-admins")
    def pending_admins() -> None:
        """Toon beheerdersaanvragen die op goedkeuring wachten."""
        pending = accounts.list_pending_admins()
        if not pending:
            click.echo("Geen aanvragen.")
        for admin in pending:
            click.echo(f"{admin.email}  organisatie: {admin.organisation.name}")

    @app.cli.command("approve-admin")
    @click.argument("email")
    @click.argument("plan", type=click.Choice([plan.value for plan in Plan]))
    def approve_admin(email: str, plan: str) -> None:
        """Keur een beheerder goed en zet het abonnement van zijn organisatie."""
        try:
            admin = accounts.approve_admin(email, Plan(plan))
        except UnknownAdmin:
            raise click.ClickException("Geen beheerder met dit e-mailadres.") from None
        click.echo(f"Goedgekeurd: {mask_email(admin.email)} met abonnement '{plan}'.")
