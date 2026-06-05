from dataclasses import dataclass, field
from typing import Optional
import re
from email_validator import validate_email, EmailNotValidError


@dataclass
class ValidationError:
    field: str
    message: str


@dataclass
class ValidationErrors:
    errors: list[ValidationError] = field(default_factory=list)

    def add(self, field: str, message: str):
        self.errors.append(ValidationError(field=field, message=message))

    def has_errors(self) -> bool:
        return len(self.errors) > 0

    def to_response(self) -> list[dict]:
        return [{"field": e.field, "message": e.message} for e in self.errors]


def validate_email_exists(email: str, errors: ValidationErrors):
    if not email or not email.strip():
        errors.add("email", "Email cannot be empty")
        return
    if len(email) > 150:
        errors.add("email", "Email must be at most 150 characters")
    try:
        validate_email(email, check_deliverability=False)
    except EmailNotValidError as e:
        error_msg = str(e)
        if "domain" in error_msg.lower() or "deliverability" in error_msg.lower():
            errors.add("email", "Email domain does not exist or cannot receive emails")
        elif "syntax" in error_msg.lower():
            errors.add("email", "Invalid email format")
        else:
            errors.add("email", f"Invalid email: {error_msg}")


def validate_phone_format(phone: str, errors: ValidationErrors):
    if phone is not None:
        if not phone.strip():
            errors.add("phone", "Phone cannot be empty spaces if provided")
            return
        if re.search(r'[a-zA-Z]', phone):
            errors.add("phone", "Phone number cannot contain letters")
            return
        if not phone.isdigit() or len(phone) != 8:
            errors.add("phone", "Phone must be exactly 8 digits without spaces or symbols")


def validate_password_strength(password: str, errors: ValidationErrors):
    if not password:
        errors.add("password", "Password cannot be empty")
        return
    if len(password) < 8:
        errors.add("password", "Password must be at least 8 characters")
    if len(password) > 255:
        errors.add("password", "Password must be at most 255 characters")
    if not re.search(r'[A-Z]', password):
        errors.add("password", "Password must contain at least one uppercase letter")
    if not re.search(r'[a-z]', password):
        errors.add("password", "Password must contain at least one lowercase letter")
    if not re.search(r'\d', password):
        errors.add("password", "Password must contain at least one number")
    if not re.search(r'[!@#$%^&*(),.?":{}|<>\-_+=\[\]\/\\]', password):
        errors.add("password", "Password must contain at least one special character")
