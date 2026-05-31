from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID
from datetime import date
from app.core.database import get_db
from app.core.validation import ValidationErrors
from app.repositories.schedule_repository import ScheduleRepository
from app.repositories.event_repository import EventRepository
from app.services.schedule_service import ScheduleService
from app.schemas.schedule import CreateEventScheduleRequest, UpdateEventScheduleRequest, EventScheduleResponse, AvailabilityResponse
from app.schemas.common import ValidationError

router = APIRouter(tags=["Event Schedules"])


def get_schedule_service(db: AsyncSession = Depends(get_db)) -> ScheduleService:
    return ScheduleService(ScheduleRepository(db), EventRepository(db))


@router.get(
    "/events/{event_id}/schedules",
    response_model=list[EventScheduleResponse],
    responses={404: {"model": ValidationError}},
)
async def list_event_schedules(
    event_id: UUID,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    schedule_service: ScheduleService = Depends(get_schedule_service),
):
    try:
        return await schedule_service.list_schedules(event_id, start_date, end_date)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.args[0])


@router.post(
    "/events/{event_id}/schedules",
    response_model=EventScheduleResponse,
    status_code=status.HTTP_201_CREATED,
    responses={400: {"model": ValidationError}, 404: {"model": ValidationError}, 422: {"model": ValidationError}},
)
async def create_event_schedule(
    event_id: UUID,
    request: CreateEventScheduleRequest,
    schedule_service: ScheduleService = Depends(get_schedule_service),
):
    errors = ValidationErrors()
    try:
        return await schedule_service.create_schedule(event_id, request, errors)
    except ValueError as e:
        detail = e.args[0]
        if any(d.get("field") == "event_id" for d in detail):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
        if any(d.get("field") == "schedule" for d in detail):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)


@router.get(
    "/schedules/{schedule_id}",
    response_model=EventScheduleResponse,
    responses={404: {"model": ValidationError}},
)
async def get_schedule(
    schedule_id: UUID,
    schedule_service: ScheduleService = Depends(get_schedule_service),
):
    try:
        return await schedule_service.get_schedule(schedule_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.args[0])


@router.put(
    "/schedules/{schedule_id}",
    response_model=EventScheduleResponse,
    responses={404: {"model": ValidationError}, 409: {"model": ValidationError}, 422: {"model": ValidationError}},
)
async def update_schedule(
    schedule_id: UUID,
    request: UpdateEventScheduleRequest,
    schedule_service: ScheduleService = Depends(get_schedule_service),
):
    errors = ValidationErrors()
    try:
        return await schedule_service.update_schedule(schedule_id, request, errors)
    except ValueError as e:
        detail = e.args[0]
        if any(d.get("field") == "schedule_id" for d in detail):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
        if any(d.get("field") == "schedule" for d in detail):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)


@router.delete(
    "/schedules/{schedule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"model": ValidationError}},
)
async def delete_schedule(
    schedule_id: UUID,
    schedule_service: ScheduleService = Depends(get_schedule_service),
):
    try:
        await schedule_service.delete_schedule(schedule_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.args[0])


@router.get(
    "/schedules/{schedule_id}/availability",
    response_model=AvailabilityResponse,
    responses={404: {"model": ValidationError}},
)
async def check_availability(
    schedule_id: UUID,
    schedule_service: ScheduleService = Depends(get_schedule_service),
):
    try:
        return await schedule_service.check_availability(schedule_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.args[0])
