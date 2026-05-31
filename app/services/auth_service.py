from app.core.validation import ValidationErrors
from app.schemas.user import RegisterRequest, LoginRequest


class NameValidator:
    @staticmethod
    def validate_name(name: str, field: str, errors: ValidationErrors):
        if len(name.strip()) < 2:
            errors.add(field, f"{field.replace('_', ' ').title()} must be at least 2 characters")
        if not name.replace(" ", "").isalpha():
            errors.add(field, f"{field.replace('_', ' ').title()} can only contain letters")


class RegistrationValidator:
    def __init__(self, validation_errors: ValidationErrors):
        self.errors = validation_errors

    def validate(self, request: RegisterRequest):
        self._validate_names(request)

    def _validate_names(self, request: RegisterRequest):
        NameValidator.validate_name(request.first_name, "first_name", self.errors)
        NameValidator.validate_name(request.last_name, "last_name", self.errors)


class LoginValidator:
    def __init__(self, validation_errors: ValidationErrors):
        self.errors = validation_errors

    def validate(self, request: LoginRequest):
        pass
