from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from typing import Optional
from uuid import UUID
from datetime import date, time
from app.core.database import get_db
from app.api.deps import get_current_user
from app.core.validation import ValidationErrors
from app.domain.models import EventSchedule, Event, User
from app.schemas.schedule import (
    CreateEventScheduleRequest,
    UpdateEventScheduleRequest,
    EventScheduleResponse,
    AvailabilityResponse,
)
from app.schemas.common import ValidationError

router = APIRouter(tags=["Event Schedules"])


def validate_schedule_times(request: CreateEventScheduleRequest | UpdateEventScheduleRequest, errors: ValidationErrors):
    if hasattr(request, "start_time") and request.start_time is not None and hasattr(request, "end_time") and request.end_time is not None:
        if request.end_time <= request.start_time:
            errors.add("end_time", "End time must be after start time")

    if hasattr(request, "schedule_date") and request.schedule_date is not None:
        if request.schedule_date < date.today():
            errors.add("schedule_date", "Schedule date cannot be in the past")


@router.get(
    "/events/{event_id}/schedules",
    response_model=list[EventScheduleResponse],
    responses={404: {"model": ValidationError}},
)
async def list_event_schedules(
    event_id: UUID,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[{"field": "event_id", "message": "Event not found"}],
        )

    query = select(EventSchedule).where(EventSchedule.event_id == event_id)

    if start_date:
        query = query.where(EventSchedule.schedule_date >= start_date)
    if end_date:
        query = query.where(EventSchedule.schedule_date <= end_date)

    result = await db.execute(query)
    schedules = result.scalars().all()

    return schedules


@router.post(
    "/events/{event_id}/schedules",
    response_model=EventScheduleResponse,
    status_code=status.HTTP_201_CREATED,
    responses={400: {"model": ValidationError}, 404: {"model": ValidationError}, 422: {"model": ValidationError}},
)
async def create_event_schedule(
    event_id: UUID,
    request: CreateEventScheduleRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[{"field": "event_id", "message": "Event not found"}],
        )

    errors = ValidationErrors()

    if request.available_slots > event.max_capacity:
        errors.add("available_slots", "Available slots cannot exceed event max capacity")

    validate_schedule_times(request, errors)

    if errors.has_errors():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=errors.to_response(),
        )

    conflict_query = select(EventSchedule).where(
        and_(
            EventSchedule.event_id == event_id,
            EventSchedule.schedule_date == request.schedule_date,
            or_(
                and_(
                    EventSchedule.start_time < request.end_time,
                    EventSchedule.end_time > request.start_time,
                ),
            ),
        ),
    )

    conflict_result = await db.execute(conflict_query)
    conflicts = conflict_result.scalars().all()

    if conflicts:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=[{"field": "schedule", "message": "Schedule conflicts with existing schedule on this date and time range"}],
        )

    new_schedule = EventSchedule(
        event_id=event_id,
        schedule_date=request.schedule_date,
        start_time=request.start_time,
        end_time=request.end_time,
        available_slots=request.available_slots,
    )

    db.add(new_schedule)
    await db.flush()
    await db.refresh(new_schedule)

    return new_schedule


@router.get(
    "/schedules/{schedule_id}",
    response_model=EventScheduleResponse,
    responses={404: {"model": ValidationError}},
)
async def get_schedule(schedule_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(EventSchedule).where(EventSchedule.id == schedule_id))
    schedule = result.scalar_one_or_none()

    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[{"field": "schedule_id", "message": "Schedule not found"}],
        )

    return schedule


@router.put(
    "/schedules/{schedule_id}",
    response_model=EventScheduleResponse,
    responses={404: {"model": ValidationError}, 409: {"model": ValidationError}, 422: {"model": ValidationError}},
)
async def update_schedule(
    schedule_id: UUID,
    request: UpdateEventScheduleRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(EventSchedule).where(EventSchedule.id == schedule_id))
    schedule = result.scalar_one_or_none()

    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[{"field": "schedule_id", "message": "Schedule not found"}],
        )

    errors = ValidationErrors()

    new_date = request.schedule_date or schedule.schedule_date
    new_start = request.start_time or schedule.start_time
    new_end = request.end_time or schedule.end_time

    class TempRequest:
        pass
    temp = TempRequest()
    temp.schedule_date = new_date
    temp.start_time = new_start
    temp.end_time = new_end
    validate_schedule_times(temp, errors)

    if request.available_slots is not None:
        event_result = await db.execute(select(Event).where(Event.id == schedule.event_id))
        event = event_result.scalar_one()
        if request.available_slots > event.max_capacity:
            errors.add("available_slots", "Available slots cannot exceed event max capacity")

    if errors.has_errors():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=errors.to_response(),
        )

    if request.schedule_date or request.start_time or request.end_time:
        check_date = request.schedule_date or schedule.schedule_date
        check_start = request.start_time or schedule.start_time
        check_end = request.end_time or schedule.end_time

        conflict_query = select(EventSchedule).where(
            and_(
                EventSchedule.event_id == schedule.event_id,
                EventSchedule.id != schedule_id,
                EventSchedule.schedule_date == check_date,
                or_(
                    and_(
                        EventSchedule.start_time < check_end,
                        EventSchedule.end_time > check_start,
                    ),
                ),
            ),
        )

        conflict_result = await db.execute(conflict_query)
        conflicts = conflict_result.scalars().all()

        if conflicts:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=[{"field": "schedule", "message": "Schedule conflicts with existing schedule"}],
            )

    update_data = request.model_dump(exclude_unset=True)
    for field_name, value in update_data.items():
        setattr(schedule, field_name, value)

    await db.flush()
    await db.refresh(schedule)

    return schedule


@router.delete(
    "/schedules/{schedule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"model": ValidationError}},
)
async def delete_schedule(
    schedule_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(EventSchedule).where(EventSchedule.id == schedule_id))
    schedule = result.scalar_one_or_none()

    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[{"field": "schedule_id", "message": "Schedule not found"}],
        )

    await db.delete(schedule)
    await db.flush()


@router.get(
    "/schedules/{schedule_id}/availability",
    response_model=AvailabilityResponse,
    responses={404: {"model": ValidationError}},
)
async def check_availability(schedule_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(EventSchedule).where(EventSchedule.id == schedule_id))
    schedule = result.scalar_one_or_none()

    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[{"field": "schedule_id", "message": "Schedule not found"}],
        )

    event_result = await db.execute(select(Event).where(Event.id == schedule.event_id))
    event = event_result.scalar_one()

    return AvailabilityResponse(
        schedule_id=schedule.id,
        available_slots=schedule.available_slots,
        max_capacity=event.max_capacity,
        is_available=schedule.available_slots > 0,
    )
