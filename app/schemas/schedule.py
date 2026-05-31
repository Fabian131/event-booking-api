from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, date, time
from uuid import UUID


class CreateEventScheduleRequest(BaseModel):
    schedule_date: date
    start_time: time
    end_time: time
    available_slots: int = Field(..., ge=1, le=32767)


class UpdateEventScheduleRequest(BaseModel):
    schedule_date: Optional[date] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    available_slots: Optional[int] = Field(None, ge=0, le=32767)


class EventScheduleResponse(BaseModel):
    id: UUID
    event_id: UUID
    schedule_date: date
    start_time: time
    end_time: time
    available_slots: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class AvailabilityResponse(BaseModel):
    schedule_id: UUID
    available_slots: int
    max_capacity: int
    is_available: bool
