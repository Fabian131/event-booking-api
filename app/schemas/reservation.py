from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, date, time
from uuid import UUID
from enum import Enum


class ReservationStatus(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"


class CreateReservationRequest(BaseModel):
    event_id: UUID
    ticket_quantity: int = Field(..., ge=1, le=100)
    notes: Optional[str] = Field(None, max_length=500)


class ReservationUserContext(BaseModel):
    user_id: UUID
    user_name: str
    user_email: str


class ReservationResponse(BaseModel):
    id: UUID
    user_id: UUID
    event_id: UUID
    event_title: str
    event_date: date
    event_start_time: time
    event_end_time: time
    ticket_quantity: int
    status: ReservationStatus
    notes: Optional[str]
    user: ReservationUserContext
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
