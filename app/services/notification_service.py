from uuid import UUID
from app.domain.models import Notification
from app.repositories.notification_repository import NotificationRepository


class NotificationService:
    def __init__(self, notification_repo: NotificationRepository):
        self.notification_repo = notification_repo

    async def list_notifications(self, user_id: UUID, page: int, limit: int, is_read: bool | None) -> tuple[list[Notification], int]:
        offset = (page - 1) * limit
        notifications = await self.notification_repo.get_by_user(user_id, offset, limit, is_read)
        total = await self.notification_repo.count(user_id=user_id)
        return notifications, total

    async def get_notification(self, notification_id: UUID, user_id: UUID) -> Notification:
        notification = await self.notification_repo.get_by_id(notification_id)
        if not notification or notification.user_id != user_id:
            raise ValueError([{"field": "notification_id", "message": "Notification not found"}])
        return notification

    async def mark_as_read(self, notification_id: UUID, user_id: UUID) -> Notification:
        notification = await self.get_notification(notification_id, user_id)

        if notification.is_read:
            raise ValueError([{"field": "is_read", "message": "Notification is already marked as read"}])

        return await self.notification_repo.update(notification, is_read=True)
