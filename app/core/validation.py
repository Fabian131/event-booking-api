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
    try:
        validate_email(email, check_deliverability=True)
    except EmailNotValidError as e:
        error_msg = str(e)
        if "domain" in error_msg.lower() or "deliverability" in error_msg.lower():
            errors.add("email", "Email domain does not exist or cannot receive emails")
        elif "syntax" in error_msg.lower():
            errors.add("email", "Invalid email format")
        else:
            errors.add("email", f"Invalid email: {error_msg}")


def validate_phone_format(phone: str, errors: ValidationErrors):
    if phone:
        cleaned = re.sub(r'[\s\-\(\)\+]', '', phone)
        if not cleaned.isdigit() or len(cleaned) < 7 or len(cleaned) > 15:
            errors.add("phone", "Phone must be 7-15 digits")


def validate_password_strength(password: str, errors: ValidationErrors):
    if len(password) < 8:
        errors.add("password", "Password must be at least 8 characters")
    if not re.search(r'[A-Z]', password):
        errors.add("password", "Password must contain at least one uppercase letter")
    if not re.search(r'[a-z]', password):
        errors.add("password", "Password must contain at least one lowercase letter")
    if not re.search(r'\d', password):
        errors.add("password", "Password must contain at least one number")
