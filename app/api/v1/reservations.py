from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID
from datetime import date as date_type
from app.core.database import get_db
from app.core.validation import ValidationErrors
from app.api.deps import get_current_user
from app.domain.models import User
from app.repositories.reservation_repository import ReservationRepository
from app.repositories.event_repository import EventRepository
from app.repositories.notification_repository import NotificationRepository
from app.services.reservation_service import ReservationService
from app.schemas.reservation import CreateReservationRequest, ReservationResponse, ReservationStatus
from app.schemas.event import CalendarDatesResponse
from app.schemas.common import PaginatedResponse, PaginationMeta, ValidationError

router = APIRouter(prefix="/reservations", tags=["Reservations"])


def get_reservation_service(db: AsyncSession = Depends(get_db)) -> ReservationService:
    return ReservationService(
        ReservationRepository(db),
        EventRepository(db),
        NotificationRepository(db),
    )


@router.get(
    "/calendar",
    response_model=CalendarDatesResponse,
    responses={
        422: {"model": ValidationError, "description": "Invalid year or month"},
        500: {"description": "Unexpected server error"},
    },
)
async def list_calendar_dates(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    current_user: User = Depends(get_current_user),
    reservation_service: ReservationService = Depends(get_reservation_service),
):
    dates = await reservation_service.list_calendar_dates(current_user.id, year, month)
    return CalendarDatesResponse(data=dates, year=year, month=month)


@router.get(
    "",
    response_model=PaginatedResponse[ReservationResponse],
)
async def list_reservations(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status_filter: Optional[ReservationStatus] = Query(None, alias="status"),
    event_id: Optional[UUID] = None,
    search: Optional[str] = None,
    date_filter: Optional[date_type] = Query(None, alias="date"),
    current_user: User = Depends(get_current_user),
    reservation_service: ReservationService = Depends(get_reservation_service),
):
    reservations, total = await reservation_service.list_reservations(
        current_user.id, current_user.role, page, limit,
        status_filter.value if status_filter else None,
        event_id, search, date_filter,
    )
    total_pages = (total + limit - 1) // limit if total > 0 else 0
    return PaginatedResponse(
        data=reservations,
        pagination=PaginationMeta(
            page=page, limit=limit, total=total,
            total_pages=total_pages,
            has_next_page=page < total_pages,
        ),
    )


@router.post(
    "",
    response_model=ReservationResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ValidationError},
        404: {"model": ValidationError},
        409: {"model": ValidationError, "description": "Capacity conflict or duplicate reservation"},
    },
)
async def create_reservation(
    request: CreateReservationRequest,
    current_user: User = Depends(get_current_user),
    reservation_service: ReservationService = Depends(get_reservation_service),
):
    errors = ValidationErrors()
    try:
        return await reservation_service.create_reservation(current_user.id, request, errors)
    except ValueError as e:
        detail = e.args[0]
        if any(d.get("field") == "event_id" and "not found" in d.get("message", "").lower() for d in detail):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
        if any(d.get("field") == "event_id" and "already" in d.get("message", "").lower() for d in detail):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)
        if any(d.get("field") == "ticket_quantity" for d in detail):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


@router.get(
    "/{reservation_id}",
    response_model=ReservationResponse,
    responses={404: {"model": ValidationError}},
)
async def get_reservation(
    reservation_id: UUID,
    current_user: User = Depends(get_current_user),
    reservation_service: ReservationService = Depends(get_reservation_service),
):
    try:
        return await reservation_service.get_reservation(reservation_id, current_user.id, current_user.role)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.args[0])


@router.patch(
    "/{reservation_id}/cancel",
    response_model=ReservationResponse,
    responses={
        400: {"model": ValidationError, "description": "Already cancelled"},
        404: {"model": ValidationError},
    },
)
async def cancel_reservation(
    reservation_id: UUID,
    current_user: User = Depends(get_current_user),
    reservation_service: ReservationService = Depends(get_reservation_service),
):
    try:
        return await reservation_service.cancel_reservation(reservation_id, current_user.id, current_user.role)
    except ValueError as e:
        detail = e.args[0]
        if any(d.get("field") == "reservation_id" for d in detail):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
