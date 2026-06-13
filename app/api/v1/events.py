from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID
from datetime import date as date_type, time as time_type
from app.core.database import get_db
from app.core.validation import ValidationErrors
from app.api.deps import require_business_user
from app.domain.models import User
from app.repositories.event_repository import EventRepository
from app.services.event_service import EventService
from app.schemas.event import CreateEventRequest, UpdateEventRequest, EventResponse, EventCategory, CalendarDatesResponse
from app.schemas.common import PaginatedResponse, PaginationMeta, ValidationError

router = APIRouter(prefix="/events", tags=["Events"])


def validation_response(status_code: int, details: list[dict], error: str = "validation_error", message: str = "One or more validation errors occurred") -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": error,
            "message": message,
            "details": details,
        },
    )


def schedule_conflict_response(details: list[dict]) -> JSONResponse:
    message = next(
        (d.get("message") for d in details if d.get("field") == "schedule"),
        "An event already occupies this date and time slot",
    )
    return validation_response(
        status.HTTP_409_CONFLICT,
        details,
        error="schedule_conflict",
        message=message,
    )


def get_event_service(db: AsyncSession = Depends(get_db)) -> EventService:
    return EventService(EventRepository(db))


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
    event_service: EventService = Depends(get_event_service),
):
    dates = await event_service.list_calendar_dates(year, month)
    return CalendarDatesResponse(data=dates, year=year, month=month)


@router.get("", response_model=PaginatedResponse[EventResponse])
async def list_events(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    date_filter: Optional[date_type] = Query(None, alias="date"),
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
        403: {"description": "Business user access required"},
        422: {"model": ValidationError},
    },
)
async def create_event(
    title: str = Form(...),
    max_capacity: int = Form(...),
    category: EventCategory = Form(...),
    date: date_type = Form(...),
    start_time: time_type = Form(...),
    end_time: time_type = Form(...),
    description: Optional[str] = Form(None),
    image: UploadFile = File(default=None),
    current_user: User = Depends(require_business_user),
    event_service: EventService = Depends(get_event_service),
):
    errors = ValidationErrors()
    request = CreateEventRequest(
        title=title,
        description=description,
        max_capacity=max_capacity,
        category=category,
        date=date,
        start_time=start_time,
        end_time=end_time,
    )
    try:
        return await event_service.create_event(request, errors, image)
    except ValueError as e:
        detail = e.args[0]
        if any(d.get("field") == "schedule" for d in detail):
            return schedule_conflict_response(detail)
        return validation_response(status.HTTP_422_UNPROCESSABLE_ENTITY, detail)


@router.get(
    "/{event_id}",
    response_model=EventResponse,
    responses={404: {"model": ValidationError}},
)
async def get_event(event_id: UUID, event_service: EventService = Depends(get_event_service)):
    try:
        return await event_service.get_event(event_id)
    except ValueError as e:
        return validation_response(status.HTTP_404_NOT_FOUND, e.args[0])


@router.put(
    "/{event_id}",
    response_model=EventResponse,
    responses={
        404: {"model": ValidationError},
        403: {"description": "Business user access required"},
        409: {"model": ValidationError, "description": "Schedule conflict"},
        422: {"model": ValidationError},
    },
)
async def update_event(
    event_id: UUID,
    req: Request,
    current_user: User = Depends(require_business_user),
    event_service: EventService = Depends(get_event_service),
):
    errors = ValidationErrors()
    form = await req.form()
    form_data: dict = {}
    for key in (
        "title", "description", "max_capacity", "category",
        "date", "start_time", "end_time", "is_active",
    ):
        val = form.get(key)
        if val is not None and val != "":
            form_data[key] = str(val)
    image = form.get("image")

    request = UpdateEventRequest(**form_data)
    try:
        return await event_service.update_event(event_id, request, errors, image)
    except ValueError as e:
        detail = e.args[0]
        if any(d.get("field") == "event_id" for d in detail):
            return validation_response(status.HTTP_404_NOT_FOUND, detail)
        if any(d.get("field") == "schedule" for d in detail):
            return schedule_conflict_response(detail)
        return validation_response(status.HTTP_422_UNPROCESSABLE_ENTITY, detail)


@router.delete(
    "/{event_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        403: {"description": "Business user access required"},
        404: {"model": ValidationError},
    },
)
async def delete_event(
    event_id: UUID,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_business_user),
    event_service: EventService = Depends(get_event_service),
):
    try:
        await event_service.delete_event(event_id, background_tasks)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.args[0])
