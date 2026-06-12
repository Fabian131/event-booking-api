from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user
from app.core.database import get_db
from app.domain.models import User
from app.schemas.user import UserResponse, PushTokenUpdate

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/me/push-token", response_model=UserResponse)
async def update_push_token(
    body: PushTokenUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(
        select(User).where(User.expo_push_token == body.push_token, User.id != current_user.id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Push token already registered to another user",
        )

    current_user.expo_push_token = body.push_token
    await db.flush()
    await db.refresh(current_user)
    return current_user


@router.delete("/me/push-token", status_code=status.HTTP_204_NO_CONTENT)
async def remove_push_token(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_user.expo_push_token = None
    await db.flush()
