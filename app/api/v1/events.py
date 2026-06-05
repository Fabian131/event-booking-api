from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID
from datetime import date, time
from app.core.database import get_db
from app.core.validation import ValidationErrors
from app.api.deps import get_current_user
from app.domain.models import User
from app.repositories.event_repository import EventRepository
from app.services.event_service import EventService
from app.schemas.event import CreateEventRequest, UpdateEventRequest, EventResponse, EventCategory
from app.schemas.common import PaginatedResponse, PaginationMeta, ValidationError

router = APIRouter(prefix="/events", tags=["Events"])


def get_event_service(db: AsyncSession = Depends(get_db)) -> EventService:
    return EventService(EventRepository(db))


@router.get("", response_model=PaginatedResponse[EventResponse])
async def list_events(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    date_filter: Optional[date] = Query(None, alias="date"),
    search: Optional[str] = None,
    category: Optional[str] = None,
    is_active: Optional[bool] = True,
    event_service: EventService = Depends(get_event_service),
):
    events, total = await event_service.list_events(
        page, limit, category, is_active, date_filter, search
    )
    total_pages = (total + limit - 1) // limit if total > 0 else 0
    return PaginatedResponse(
        data=events,
        pagination=PaginationMeta(
            page=page, limit=limit, total=total,
            total_pages=total_pages,
            has_next_page=page < total_pages,
        ),
    )


@router.post(
    "",
    response_model=EventResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        409: {"model": ValidationError, "description": "Schedule conflict"},
        422: {"model": ValidationError},
    },
)
async def create_event(
    title: str = Form(...),
    max_capacity: int = Form(...),
    category: EventCategory = Form(...),
    event_date: date = Form(..., alias="date"),
    start_time: time = Form(...),
    end_time: time = Form(...),
    description: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
    event_service: EventService = Depends(get_event_service),
):
    errors = ValidationErrors()
    request = CreateEventRequest(
        title=title,
        description=description,
        max_capacity=max_capacity,
        category=category,
        date=event_date,
        start_time=start_time,
        end_time=end_time,
    )
    try:
        return await event_service.create_event(request, errors)
    except ValueError as e:
        detail = e.args[0]
        if any(d.get("field") == "schedule" for d in detail):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)


@router.get(
    "/{event_id}",
    response_model=EventResponse,
    responses={404: {"model": ValidationError}},
)
async def get_event(event_id: UUID, event_service: EventService = Depends(get_event_service)):
    try:
        return await event_service.get_event(event_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.args[0])


@router.put(
    "/{event_id}",
    response_model=EventResponse,
    responses={
        404: {"model": ValidationError},
        409: {"model": ValidationError, "description": "Schedule conflict"},
        422: {"model": ValidationError},
    },
)
async def update_event(
    event_id: UUID,
    title: Optional[str] = Form(None),
    max_capacity: Optional[int] = Form(None),
    category: Optional[EventCategory] = Form(None),
    event_date: Optional[date] = Form(None, alias="date"),
    start_time: Optional[time] = Form(None),
    end_time: Optional[time] = Form(None),
    description: Optional[str] = Form(None),
    is_active: Optional[bool] = Form(None),
    image: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
    event_service: EventService = Depends(get_event_service),
):
    errors = ValidationErrors()
    request = UpdateEventRequest(
        title=title,
        description=description,
        max_capacity=max_capacity,
        category=category,
        date=event_date,
        start_time=start_time,
        end_time=end_time,
        is_active=is_active,
    )
    try:
        return await event_service.update_event(event_id, request, errors)
    except ValueError as e:
        detail = e.args[0]
        if any(d.get("field") == "event_id" for d in detail):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
        if any(d.get("field") == "schedule" for d in detail):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)


@router.delete(
    "/{event_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"model": ValidationError}},
)
async def delete_event(
    event_id: UUID,
    current_user: User = Depends(get_current_user),
    event_service: EventService = Depends(get_event_service),
):
    try:
        await event_service.delete_event(event_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.args[0])
