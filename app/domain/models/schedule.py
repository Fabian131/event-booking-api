import uuid
from datetime import datetime, date, time
from sqlalchemy import SmallInteger, Date, Time, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class EventSchedule(Base):
    __tablename__ = "event_schedules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    schedule_date: Mapped[date] = mapped_column(Date, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    available_slots: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    event: Mapped["Event"] = relationship("Event", back_populates="schedules")
    reservations: Mapped[list["Reservation"]] = relationship("Reservation", back_populates="event_schedule", lazy="selectin")

    __table_args__ = (
        CheckConstraint('end_time > start_time', name='ck_event_schedules_time_range'),
        CheckConstraint('available_slots >= 0', name='ck_event_schedules_available_slots'),
    )
