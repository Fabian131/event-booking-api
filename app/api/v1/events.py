from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID
from app.core.database import get_db
from app.core.validation import ValidationErrors
from app.repositories.event_repository import EventRepository
from app.services.event_service import EventService
from app.schemas.event import CreateEventRequest, UpdateEventRequest, EventResponse
from app.schemas.common import PaginatedResponse, PaginationMeta, ValidationError

router = APIRouter(prefix="/events", tags=["Events"])


def get_event_service(db: AsyncSession = Depends(get_db)) -> EventService:
    return EventService(EventRepository(db))


@router.get("", response_model=PaginatedResponse[EventResponse])
async def list_events(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    category: Optional[str] = None,
    is_active: Optional[bool] = True,
    event_service: EventService = Depends(get_event_service),
):
    events, total = await event_service.list_events(page, limit, category, is_active)
    return PaginatedResponse(
        data=events,
        pagination=PaginationMeta(page=page, limit=limit, total=total, total_pages=(total + limit - 1) // limit),
    )


@router.post(
    "",
    response_model=EventResponse,
    status_code=status.HTTP_201_CREATED,
    responses={422: {"model": ValidationError}},
)
async def create_event(
    request: CreateEventRequest,
    event_service: EventService = Depends(get_event_service),
):
    errors = ValidationErrors()
    try:
        return await event_service.create_event(request, errors)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.args[0])


@router.get("/{event_id}", response_model=EventResponse, responses={404: {"model": ValidationError}})
async def get_event(event_id: UUID, event_service: EventService = Depends(get_event_service)):
    try:
        return await event_service.get_event(event_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.args[0])


@router.put(
    "/{event_id}",
    response_model=EventResponse,
    responses={404: {"model": ValidationError}, 422: {"model": ValidationError}},
)
async def update_event(
    event_id: UUID,
    request: UpdateEventRequest,
    event_service: EventService = Depends(get_event_service),
):
    errors = ValidationErrors()
    try:
        return await event_service.update_event(event_id, request, errors)
    except ValueError as e:
        detail = e.args[0]
        status_code = status.HTTP_404_NOT_FOUND if any(d.get("field") == "event_id" for d in detail) else status.HTTP_422_UNPROCESSABLE_ENTITY
        raise HTTPException(status_code=status_code, detail=detail)


@router.delete(
    "/{event_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"model": ValidationError}},
)
async def delete_event(
    event_id: UUID,
    event_service: EventService = Depends(get_event_service),
):
    try:
        await event_service.delete_event(event_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.args[0])
