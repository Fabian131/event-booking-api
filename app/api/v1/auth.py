from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.validation import ValidationErrors
from app.repositories.user_repository import UserRepository
from app.services.user_service import AuthService
from app.schemas.user import RegisterRequest, LoginRequest, TokenResponse, UserResponse
from app.schemas.common import ValidationError

router = APIRouter(prefix="/auth", tags=["Authentication"])


def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    return AuthService(UserRepository(db))


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        409: {"model": ValidationError, "description": "Duplicate email or phone"},
        422: {"model": ValidationError, "description": "Validation errors"},
    },
)
async def register(request: RegisterRequest, auth_service: AuthService = Depends(get_auth_service)):
    errors = ValidationErrors()
    try:
        return await auth_service.register(request, errors)
    except ValueError as e:
        detail = e.args[0]
        status_code = status.HTTP_409_CONFLICT if any(d.get("message") in ("Email already registered", "Phone number already registered") for d in detail) else status.HTTP_422_UNPROCESSABLE_ENTITY
        raise HTTPException(status_code=status_code, detail=detail)


@router.post(
    "/login",
    response_model=TokenResponse,
    responses={
        401: {"model": ValidationError, "description": "Invalid credentials or inactive account"},
        422: {"model": ValidationError, "description": "Validation errors"},
    },
)
async def login(request: LoginRequest, auth_service: AuthService = Depends(get_auth_service)):
    errors = ValidationErrors()
    try:
        return await auth_service.login(request, errors)
    except ValueError as e:
        detail = e.args[0]
        status_code = status.HTTP_401_UNAUTHORIZED if any(d.get("field") in ("credentials", "account") for d in detail) else status.HTTP_422_UNPROCESSABLE_ENTITY
        raise HTTPException(status_code=status_code, detail=detail)
