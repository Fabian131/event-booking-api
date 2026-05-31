from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID
from enum import Enum


class ReservationStatus(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"


class CreateReservationRequest(BaseModel):
    event_schedule_id: UUID
    quantity: int = Field(..., ge=1, le=100)
    notes: Optional[str] = Field(None, max_length=500)


class ReservationResponse(BaseModel):
    id: UUID
    user_id: UUID
    event_schedule_id: UUID
    status: ReservationStatus
    quantity: int
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
