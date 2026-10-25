from sqlalchemy import Boolean, CheckConstraint, ForeignKey, ForeignKeyConstraint, String
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db
from app.models.enums import Role, enum_column_type

MIN_PASSWORD_LENGTH = 12


def normalise_email(email: str) -> str:
    return email.strip().lower()


class User(db.Model):
    """Beheerder (beheert accounts) of gewoon account (alleen inloggen, eigen team)."""

    __tablename__ = "users"
    __table_args__ = (
        # Het team van een gebruiker moet bij dezelfde organisatie horen.
        # Bij team_id = NULL (beheerder) wordt deze koppeling niet gecontroleerd.
        ForeignKeyConstraint(
            ["team_id", "organisation_id"],
            ["teams.id", "teams.organisation_id"],
        ),
        # Een gewoon account hoort altijd bij een team.
        CheckConstraint("role = 'admin' OR team_id IS NOT NULL", name="member_needs_team"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(enum_column_type(Role), default=Role.MEMBER)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    organisation_id: Mapped[int] = mapped_column(ForeignKey("organisations.id"), index=True)
    team_id: Mapped[int | None] = mapped_column(index=True, default=None)

    organisation: Mapped["Organisation"] = relationship(back_populates="users")  # noqa: F821
    # Alleen team_id schrijven; organisation_id komt uit de relatie met Organisation.
    team: Mapped["Team | None"] = relationship(  # noqa: F821
        back_populates="users",
        primaryjoin="User.team_id == Team.id",
        foreign_keys=[team_id],
    )

    @validates("email")
    def _normalise_email(self, _key: str, value: str) -> str:
        return normalise_email(value)

    def set_password(self, password: str) -> None:
        if len(password) < MIN_PASSWORD_LENGTH:
            raise ValueError(f"Wachtwoord moet minimaal {MIN_PASSWORD_LENGTH} tekens hebben.")
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)
