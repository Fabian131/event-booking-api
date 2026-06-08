from pydantic import BaseModel, Field
from typing import Optional, Union
from datetime import datetime, date, time
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
    date: date
    start_time: time
    end_time: time


class UpdateEventRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=64)
    description: Optional[str] = Field(None, max_length=255)
    max_capacity: Optional[int] = Field(None, ge=1, le=9999999)
    category: Union[EventCategory, None] = None
    date: Union[date, None] = None
    start_time: Union[time, None] = None
    end_time: Union[time, None] = None
    is_active: Union[bool, None] = None


class EventResponse(BaseModel):
    id: UUID
    title: str
    description: Optional[str]
    image_url: Optional[str]
    max_capacity: int
    remaining_capacity: int
    category: str
    date: date
    start_time: time
    end_time: time
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
