from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.api.deps import get_current_user
from app.domain.models import User
from app.repositories.user_device_token_repository import UserDeviceTokenRepository
from app.services.device_token_service import DeviceTokenService
from app.schemas.device_token import RegisterDeviceTokenRequest, DeviceTokenResponse
from app.schemas.common import ValidationError

router = APIRouter(prefix="/device-tokens", tags=["Device Tokens"])


def get_device_token_service(db: AsyncSession = Depends(get_db)) -> DeviceTokenService:
    return DeviceTokenService(UserDeviceTokenRepository(db))


@router.post(
    "",
    response_model=DeviceTokenResponse,
    status_code=status.HTTP_200_OK,
    responses={422: {"model": ValidationError}},
    summary="Register or update an Expo push token for the current user",
    description=(
        "Saves the Expo push token associated with the authenticated user's device. "
        "If the token already exists it is reactivated. "
        "Call this endpoint after login and on every `onNewToken` event from the Expo SDK."
    ),
)
async def register_device_token(
    request: RegisterDeviceTokenRequest,
    current_user: User = Depends(get_current_user),
    device_token_service: DeviceTokenService = Depends(get_device_token_service),
):
    try:
        token = await device_token_service.register_token(
            user_id=current_user.id,
            token=request.token,
            platform=request.platform,
        )
        return token
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )
