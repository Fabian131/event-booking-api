from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import timedelta
from app.core.database import get_db
from app.core.security import verify_password, get_password_hash, create_access_token
from app.core.config import settings
from app.core.validation import (
    ValidationErrors,
    validate_email_exists,
    validate_phone_format,
    validate_password_strength,
)
from app.domain.models import User
from app.schemas.user import RegisterRequest, LoginRequest, TokenResponse, UserResponse
from app.schemas.common import ValidationError

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        409: {"model": ValidationError, "description": "Duplicate email or phone"},
        422: {"model": ValidationError, "description": "Validation errors"},
    },
)
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)):
    errors = ValidationErrors()

    if len(request.first_name.strip()) < 2:
        errors.add("first_name", "First name must be at least 2 characters")
    if len(request.last_name.strip()) < 2:
        errors.add("last_name", "Last name must be at least 2 characters")
    if not request.first_name.replace(" ", "").isalpha():
        errors.add("first_name", "First name can only contain letters")
    if not request.last_name.replace(" ", "").isalpha():
        errors.add("last_name", "Last name can only contain letters")

    validate_email_exists(request.email, errors)
    validate_phone_format(request.phone, errors)
    validate_password_strength(request.password, errors)

    if errors.has_errors():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=errors.to_response(),
        )

    result = await db.execute(select(User).where(User.email == request.email))
    existing_user = result.scalar_one_or_none()

    result_phone = None
    if request.phone:
        result_phone = await db.execute(select(User).where(User.phone == request.phone))
        existing_phone = result_phone.scalar_one_or_none()
    else:
        existing_phone = None

    duplicate_errors = ValidationErrors()
    if existing_user:
        duplicate_errors.add("email", "Email already registered")
    if existing_phone:
        duplicate_errors.add("phone", "Phone number already registered")

    if duplicate_errors.has_errors():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=duplicate_errors.to_response(),
        )

    new_user = User(
        first_name=request.first_name.strip(),
        last_name=request.last_name.strip(),
        email=request.email,
        phone=request.phone,
        password_hash=get_password_hash(request.password),
    )

    db.add(new_user)
    await db.flush()
    await db.refresh(new_user)

    return new_user


@router.post(
    "/login",
    response_model=TokenResponse,
    responses={
        401: {"model": ValidationError, "description": "Invalid credentials or inactive account"},
        422: {"model": ValidationError, "description": "Validation errors"},
    },
)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    errors = ValidationErrors()
    validate_email_exists(request.email, errors)

    if errors.has_errors():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=errors.to_response(),
        )

    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=[{"field": "credentials", "message": "Invalid email or password"}],
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=[{"field": "account", "message": "User account is inactive"}],
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expires,
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
