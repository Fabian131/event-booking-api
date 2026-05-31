from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID


class CreateEventRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=150)
    description: Optional[str] = None
    location: str = Field(..., min_length=3, max_length=100)
    max_capacity: int = Field(..., ge=1, le=32767)
    category: str = Field(..., min_length=3, max_length=50)


class UpdateEventRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=150)
    description: Optional[str] = None
    location: Optional[str] = Field(None, min_length=3, max_length=100)
    max_capacity: Optional[int] = Field(None, ge=1, le=32767)
    category: Optional[str] = Field(None, min_length=3, max_length=50)
    is_active: Optional[bool] = None


class EventResponse(BaseModel):
    id: UUID
    title: str
    description: Optional[str]
    location: str
    max_capacity: int
    category: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
