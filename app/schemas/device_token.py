from pydantic import BaseModel, field_validator
from typing import Literal
from uuid import UUID
from datetime import datetime


class RegisterDeviceTokenRequest(BaseModel):
    token: str
    platform: Literal["android", "ios"] = "android"

    @field_validator("token")
    @classmethod
    def token_must_not_be_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("token must not be empty")
        return v


class DeviceTokenResponse(BaseModel):
    id: UUID
    user_id: UUID
    token: str
    platform: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
