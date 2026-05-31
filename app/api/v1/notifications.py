from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from uuid import UUID
from app.core.database import get_db
from app.api.deps import get_current_user
from app.domain.models import Notification, User
from app.schemas.notification import NotificationResponse
from app.schemas.common import PaginatedResponse, PaginationMeta, ValidationError

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get(
    "",
    response_model=PaginatedResponse[NotificationResponse],
)
async def list_notifications(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    is_read: Optional[bool] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Notification).where(Notification.user_id == current_user.id)

    if is_read is not None:
        query = query.where(Notification.is_read == is_read)

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    query = query.offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    notifications = result.scalars().all()

    return PaginatedResponse(
        data=notifications,
        pagination=PaginationMeta(
            page=page,
            limit=limit,
            total=total,
            total_pages=(total + limit - 1) // limit,
        ),
    )


@router.post(
    "/{notification_id}/read",
    response_model=NotificationResponse,
    responses={400: {"model": ValidationError}, 404: {"model": ValidationError}},
)
async def mark_notification_as_read(
    notification_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == current_user.id,
        )
    )
    notification = result.scalar_one_or_none()

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[{"field": "notification_id", "message": "Notification not found"}],
        )

    if notification.is_read:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=[{"field": "is_read", "message": "Notification is already marked as read"}],
        )

    notification.is_read = True
    await db.flush()
    await db.refresh(notification)

    return notification
