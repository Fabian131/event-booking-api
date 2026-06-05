from datetime import timedelta
from app.core.config import settings
from app.core.security import create_access_token, verify_password, get_password_hash
from app.core.validation import ValidationErrors, validate_email_exists, validate_phone_format, validate_password_strength
from app.domain.models import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import RegisterRequest, LoginRequest
from app.services.auth_service import RegistrationValidator


class AuthService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    async def register(self, request: RegisterRequest, errors: ValidationErrors) -> User:
        self._validate_registration(request, errors)
        if errors.has_errors():
            raise ValueError(errors.to_response())

        existing_user = await self.user_repo.get_by_email(request.email)
        existing_phone = await self.user_repo.get_by_phone(request.phone) if request.phone else None

        duplicate_errors = ValidationErrors()
        if existing_user:
            duplicate_errors.add("email", "Email already registered")
        if existing_phone:
            duplicate_errors.add("phone", "Phone number already registered")

        if duplicate_errors.has_errors():
            raise ValueError(duplicate_errors.to_response())

        return await self.user_repo.create(
            first_name=request.first_name.strip(),
            last_name=request.last_name.strip(),
            email=request.email,
            phone=request.phone,
            password_hash=get_password_hash(request.password),
        )

    async def login(self, request: LoginRequest, errors: ValidationErrors) -> dict:
        validate_email_exists(request.email, errors)
        if errors.has_errors():
            raise ValueError(errors.to_response())

        user = await self.user_repo.get_by_email(request.email)
        if not user or not verify_password(request.password, user.password_hash):
            raise ValueError([{"field": "credentials", "message": "Invalid email or password"}])

        if not user.is_active:
            raise ValueError([{"field": "account", "message": "User account is inactive"}])

        access_token = self._generate_token(user.id)
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user": {
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "role": user.role,
            },
        }

    def _validate_registration(self, request: RegisterRequest, errors: ValidationErrors):
        RegistrationValidator(errors).validate(request)
        validate_email_exists(request.email, errors)
        validate_phone_format(request.phone, errors)
        validate_password_strength(request.password, errors)

    def _generate_token(self, user_id: str) -> str:
        expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        return create_access_token(data={"sub": str(user_id)}, expires_delta=expires_delta)
