from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID
from app.core.database import get_db
from app.api.deps import get_current_user
from app.domain.models import User
from app.repositories.notification_repository import NotificationRepository
from app.services.notification_service import NotificationService
from app.schemas.notification import NotificationResponse
from app.schemas.common import PaginatedResponse, PaginationMeta, ValidationError

router = APIRouter(prefix="/notifications", tags=["Notifications"])


def get_notification_service(db: AsyncSession = Depends(get_db)) -> NotificationService:
    return NotificationService(NotificationRepository(db))


@router.get(
    "",
    response_model=PaginatedResponse[NotificationResponse],
)
async def list_notifications(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    is_read: Optional[bool] = None,
    current_user: User = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service),
):
    notifications, total = await notification_service.list_notifications(current_user.id, page, limit, is_read)
    total_pages = (total + limit - 1) // limit if total > 0 else 0
    return PaginatedResponse(
        data=notifications,
        pagination=PaginationMeta(
            page=page, limit=limit, total=total,
            total_pages=total_pages,
            has_next_page=page < total_pages,
        ),
    )


@router.patch(
    "/{notification_id}/read",
    response_model=NotificationResponse,
    responses={400: {"model": ValidationError}, 404: {"model": ValidationError}},
)
async def mark_notification_as_read(
    notification_id: UUID,
    current_user: User = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service),
):
    try:
        return await notification_service.mark_as_read(notification_id, current_user.id)
    except ValueError as e:
        detail = e.args[0]
        if any(d.get("field") == "notification_id" for d in detail):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
