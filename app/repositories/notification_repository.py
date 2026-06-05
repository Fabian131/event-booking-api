from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from uuid import UUID
from app.domain.models import Notification
from app.repositories.base_repository import BaseRepository


class NotificationRepository(BaseRepository[Notification]):
    def __init__(self, db: AsyncSession):
        super().__init__(Notification, db)

    async def get_by_user(self, user_id: UUID, offset: int = 0, limit: int = 20, is_read: bool | None = None) -> list[Notification]:
        query = select(Notification).where(Notification.user_id == user_id)
        if is_read is not None:
            query = query.where(Notification.is_read == is_read)
        query = query.order_by(Notification.created_at.desc())
        query = query.offset(offset).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def count_by_user(self, user_id: UUID, is_read: bool | None = None) -> int:
        query = select(func.count()).select_from(Notification).where(Notification.user_id == user_id)
        if is_read is not None:
            query = query.where(Notification.is_read == is_read)
        result = await self.db.execute(query)
        return result.scalar()

    async def create_notification(
        self,
        user_id: UUID,
        notification_type: str,
        title: str,
        message: str,
        reservation_id: UUID | None = None,
        event_id: UUID | None = None,
    ) -> Notification:
        return await self.create(
            user_id=user_id,
            type=notification_type,
            title=title,
            message=message,
            reservation_id=reservation_id,
            event_id=event_id,
        )
