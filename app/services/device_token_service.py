from uuid import UUID
from app.domain.models.user_device_token import UserDeviceToken
from app.repositories.user_device_token_repository import UserDeviceTokenRepository


class DeviceTokenService:
    def __init__(self, device_token_repo: UserDeviceTokenRepository):
        self.device_token_repo = device_token_repo

    async def register_token(self, user_id: UUID, token: str, platform: str) -> UserDeviceToken:
        """Register or reactivate a device token for the given user."""
        return await self.device_token_repo.upsert(user_id, token, platform)
