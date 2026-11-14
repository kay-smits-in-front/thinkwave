from collections.abc import Callable
from functools import wraps

from flask import abort
from flask_login import current_user, login_required

from app.models import Role, User


def me() -> User:
    """De ingelogde gebruiker als echt User-object (current_user is een proxy)."""
    return current_user._get_current_object()


def admin_required(view: Callable) -> Callable:
    """Alleen beheerders. Anderen krijgen 404, zodat de pagina niet eens lijkt te bestaan."""

    @wraps(view)
    @login_required
    def wrapper(*args, **kwargs):
        if me().role is not Role.ADMIN:
            abort(404)
        return view(*args, **kwargs)

    return wrapper
