from datetime import UTC, datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.enums import SEAT_LIMITS, Plan, enum_column_type


class Organisation(db.Model):
    """De klant. Alle andere data hangt hieraan en wordt hierop afgeschermd."""

    __tablename__ = "organisations"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    plan: Mapped[Plan | None] = mapped_column(enum_column_type(Plan), default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    teams: Mapped[list["Team"]] = relationship(back_populates="organisation")  # noqa: F821
    users: Mapped[list["User"]] = relationship(back_populates="organisation")  # noqa: F821

    def seat_limit(self) -> int | None:
        """Maximaal aantal gewone accounts. None = onbeperkt. Zonder abonnement: 0."""
        if self.plan is None:
            return 0
        return SEAT_LIMITS[self.plan]
