from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.domain.models.user_device_token import UserDeviceToken
from app.repositories.base_repository import BaseRepository


class UserDeviceTokenRepository(BaseRepository[UserDeviceToken]):
    def __init__(self, db: AsyncSession):
        super().__init__(UserDeviceToken, db)

    async def get_by_token(self, token: str) -> UserDeviceToken | None:
        result = await self.db.execute(
            select(UserDeviceToken).where(UserDeviceToken.token == token)
        )
        return result.scalar_one_or_none()

    async def get_active_by_user_ids(self, user_ids: list[UUID]) -> list[UserDeviceToken]:
        if not user_ids:
            return []
        result = await self.db.execute(
            select(UserDeviceToken).where(
                UserDeviceToken.user_id.in_(user_ids),
                UserDeviceToken.is_active == True,
            )
        )
        return result.scalars().all()

    async def get_active_by_user_id(self, user_id: UUID) -> list[UserDeviceToken]:
        result = await self.db.execute(
            select(UserDeviceToken).where(
                UserDeviceToken.user_id == user_id,
                UserDeviceToken.is_active == True,
            )
        )
        return result.scalars().all()

    async def upsert(self, user_id: UUID, token: str, platform: str) -> UserDeviceToken:
        existing = await self.get_by_token(token)
        if existing:
            return await self.update(existing, is_active=True, platform=platform, user_id=user_id)
        return await self.create(user_id=user_id, token=token, platform=platform, is_active=True)
