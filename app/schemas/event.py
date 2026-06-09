from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, date as date_type, time as time_type
from uuid import UUID
from enum import Enum


class EventCategory(str, Enum):
    SPORTS = "sports"
    MUSIC = "music"
    CULTURE = "culture"
    GASTRONOMY = "gastronomy"
    WELLNESS = "wellness"
    EDUCATION = "education"
    OTHER = "other"


class CreateEventRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=64)
    description: Optional[str] = Field(None, max_length=255)
    max_capacity: int = Field(..., ge=1, le=9999999)
    category: EventCategory
    date: date_type
    start_time: time_type
    end_time: time_type


class UpdateEventRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=64)
    description: Optional[str] = Field(None, max_length=255)
    max_capacity: Optional[int] = Field(None, ge=1, le=9999999)
    category: Optional[EventCategory] = None
    date: Optional[date_type] = None
    start_time: Optional[time_type] = None
    end_time: Optional[time_type] = None
    is_active: Optional[bool] = None


class EventResponse(BaseModel):
    id: UUID
    title: str
    description: Optional[str]
    image_url: Optional[str]
    max_capacity: int
    remaining_capacity: int
    category: str
    date: date_type
    start_time: time_type
    end_time: time_type
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CalendarDateItem(BaseModel):
    date: date_type
    count: int


class CalendarDatesResponse(BaseModel):
    data: list[CalendarDateItem]
    year: int
    month: int
