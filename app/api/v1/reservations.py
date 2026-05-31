from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from uuid import UUID
from datetime import date
from app.core.database import get_db
from app.api.deps import get_current_user
from app.core.validation import ValidationErrors
from app.domain.models import Reservation, EventSchedule, User
from app.schemas.reservation import CreateReservationRequest, ReservationResponse, ReservationStatus
from app.schemas.common import PaginatedResponse, PaginationMeta, ValidationError

router = APIRouter(prefix="/reservations", tags=["Reservations"])


@router.get(
    "",
    response_model=PaginatedResponse[ReservationResponse],
)
async def list_reservations(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status_filter: Optional[ReservationStatus] = Query(None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Reservation).where(Reservation.user_id == current_user.id)

    if status_filter:
        query = query.where(Reservation.status == status_filter.value)

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    query = query.offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    reservations = result.scalars().all()

    return PaginatedResponse(
        data=reservations,
        pagination=PaginationMeta(
            page=page,
            limit=limit,
            total=total,
            total_pages=(total + limit - 1) // limit,
        ),
    )


@router.post(
    "",
    response_model=ReservationResponse,
    status_code=status.HTTP_201_CREATED,
    responses={400: {"model": ValidationError}, 404: {"model": ValidationError}, 409: {"model": ValidationError}},
)
async def create_reservation(
    request: CreateReservationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(EventSchedule).where(EventSchedule.id == request.event_schedule_id)
    )
    schedule = result.scalar_one_or_none()

    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[{"field": "event_schedule_id", "message": "Schedule not found"}],
        )

    errors = ValidationErrors()

    if schedule.schedule_date < date.today():
        errors.add("event_schedule_id", "Cannot reserve a past schedule")

    if schedule.available_slots < request.quantity:
        errors.add("quantity", f"Only {schedule.available_slots} slots available, requested {request.quantity}")

    if errors.has_errors():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=errors.to_response(),
        )

    existing_result = await db.execute(
        select(Reservation).where(
            Reservation.user_id == current_user.id,
            Reservation.event_schedule_id == request.event_schedule_id,
            Reservation.status.in_(["PENDING", "CONFIRMED"]),
        )
    )
    existing = existing_result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=[{"field": "event_schedule_id", "message": "You already have an active reservation for this schedule"}],
        )

    new_reservation = Reservation(
        user_id=current_user.id,
        event_schedule_id=request.event_schedule_id,
        quantity=request.quantity,
        notes=request.notes,
        status=ReservationStatus.PENDING.value,
    )

    schedule.available_slots -= request.quantity

    db.add(new_reservation)
    await db.flush()
    await db.refresh(new_reservation)

    return new_reservation


@router.get(
    "/{reservation_id}",
    response_model=ReservationResponse,
    responses={404: {"model": ValidationError}},
)
async def get_reservation(
    reservation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Reservation).where(
            Reservation.id == reservation_id,
            Reservation.user_id == current_user.id,
        )
    )
    reservation = result.scalar_one_or_none()

    if not reservation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[{"field": "reservation_id", "message": "Reservation not found"}],
        )

    return reservation


@router.post(
    "/{reservation_id}/confirm",
    response_model=ReservationResponse,
    responses={400: {"model": ValidationError}, 404: {"model": ValidationError}},
)
async def confirm_reservation(
    reservation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Reservation).where(
            Reservation.id == reservation_id,
            Reservation.user_id == current_user.id,
        )
    )
    reservation = result.scalar_one_or_none()

    if not reservation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[{"field": "reservation_id", "message": "Reservation not found"}],
        )

    if reservation.status == ReservationStatus.CONFIRMED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=[{"field": "status", "message": "Reservation is already confirmed"}],
        )

    if reservation.status == ReservationStatus.CANCELLED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=[{"field": "status", "message": "Cannot confirm a cancelled reservation"}],
        )

    reservation.status = ReservationStatus.CONFIRMED.value
    await db.flush()
    await db.refresh(reservation)

    return reservation


@router.post(
    "/{reservation_id}/cancel",
    response_model=ReservationResponse,
    responses={400: {"model": ValidationError}, 404: {"model": ValidationError}},
)
async def cancel_reservation(
    reservation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Reservation).where(
            Reservation.id == reservation_id,
            Reservation.user_id == current_user.id,
        )
    )
    reservation = result.scalar_one_or_none()

    if not reservation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[{"field": "reservation_id", "message": "Reservation not found"}],
        )

    if reservation.status == ReservationStatus.CANCELLED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=[{"field": "status", "message": "Reservation is already cancelled"}],
        )

    schedule_result = await db.execute(
        select(EventSchedule).where(EventSchedule.id == reservation.event_schedule_id)
    )
    schedule = schedule_result.scalar_one()

    schedule.available_slots += reservation.quantity
    reservation.status = ReservationStatus.CANCELLED.value

    await db.flush()
    await db.refresh(reservation)

    return reservation
