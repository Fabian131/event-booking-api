import uuid
from datetime import datetime
from sqlalchemy import String, Text, SmallInteger, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class Reservation(Base):
    __tablename__ = "reservations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    event_schedule_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("event_schedules.id", ondelete="RESTRICT"), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDING")
    quantity: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="reservations")
    event_schedule: Mapped["EventSchedule"] = relationship("EventSchedule", back_populates="reservations")
    notifications: Mapped[list["Notification"]] = relationship("Notification", back_populates="reservation", lazy="selectin")

    __table_args__ = (
        CheckConstraint('quantity > 0', name='ck_reservations_quantity'),
        CheckConstraint("status IN ('PENDING', 'CONFIRMED', 'CANCELLED')", name='ck_reservations_status'),
    )
