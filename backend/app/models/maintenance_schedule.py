from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class MaintenanceSchedule(Base):
    __tablename__ = "maintenance_schedules"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True
    )

    vehicle_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("vehicles.id", ondelete="CASCADE"),
        nullable=False
    )

    service_type: Mapped[str] = mapped_column(
        String(100), nullable=False
    )

    # A schedule uses mileage or time, not both.
    interval_miles: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )

    interval_days: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )

    due_mileage: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )

    due_date: Mapped[date | None] = mapped_column(
        Date, nullable=True
    )

    notes: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
