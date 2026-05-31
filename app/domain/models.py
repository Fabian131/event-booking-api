import uuid
from datetime import datetime, date, time
from sqlalchemy import String, Text, Boolean, SmallInteger, Date, Time, DateTime, ForeignKey, CheckConstraint, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class User(Base):
    __tablename__ = "users"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    first_name: Mapped[str] = mapped_column(String(50), nullable=False)
    last_name: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[str] = mapped_column(String(150), unique=True, nullable=False, index=True)
    phone: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    reservations: Mapped[list["Reservation"]] = relationship("Reservation", back_populates="user", lazy="selectin")
    notifications: Mapped[list["Notification"]] = relationship("Notification", back_populates="user", lazy="selectin")


class Event(Base):
    __tablename__ = "events"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    location: Mapped[str] = mapped_column(String(100), nullable=False)
    max_capacity: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    schedules: Mapped[list["EventSchedule"]] = relationship("EventSchedule", back_populates="event", lazy="selectin", cascade="all, delete-orphan")
    
    __table_args__ = (
        CheckConstraint('max_capacity > 0', name='ck_events_max_capacity'),
    )


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


class Notification(Base):
    __tablename__ = "notifications"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    reservation_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("reservations.id", ondelete="SET NULL"), nullable=True)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    
    user: Mapped["User"] = relationship("User", back_populates="notifications")
    reservation: Mapped["Reservation | None"] = relationship("Reservation", back_populates="notifications")
