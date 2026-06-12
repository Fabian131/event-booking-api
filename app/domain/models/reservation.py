import uuid
from datetime import datetime
from sqlalchemy import String, Text, SmallInteger, DateTime, ForeignKey, CheckConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Reservation(Base):
    __tablename__ = "reservations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    event_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("events.id", ondelete="RESTRICT"), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="CONFIRMED")
    ticket_quantity: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="reservations")
    event: Mapped["Event"] = relationship("Event", back_populates="reservations")
    notifications: Mapped[list["Notification"]] = relationship("Notification", back_populates="reservation", lazy="selectin")

    __table_args__ = (
        CheckConstraint('ticket_quantity > 0', name='ck_reservations_ticket_quantity'),
        CheckConstraint("status IN ('CONFIRMED', 'CANCELLED')", name='ck_reservations_status'),
    )
