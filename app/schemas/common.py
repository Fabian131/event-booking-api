from pydantic import BaseModel
from typing import List, Optional, Generic, TypeVar

T = TypeVar('T')


class Error(BaseModel):
    error: str
    message: str
    details: Optional[dict] = None


class ValidationErrorDetail(BaseModel):
    field: str
    message: str


class ValidationError(BaseModel):
    error: str = "validation_error"
    message: str = "One or more validation errors occurred"
    details: List[ValidationErrorDetail]


class PaginationMeta(BaseModel):
    page: int
    limit: int
    total: int
    total_pages: int
    has_next_page: bool


class PaginatedResponse(BaseModel, Generic[T]):
    data: List[T]
    pagination: PaginationMeta
