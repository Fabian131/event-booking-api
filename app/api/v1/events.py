from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from uuid import UUID
from app.core.database import get_db
from app.api.deps import get_current_user
from app.core.validation import ValidationErrors
from app.domain.models import Event, User
from app.schemas.event import CreateEventRequest, UpdateEventRequest, EventResponse
from app.schemas.common import PaginatedResponse, PaginationMeta, ValidationError

router = APIRouter(prefix="/events", tags=["Events"])


def validate_event_data(request: CreateEventRequest | UpdateEventRequest, errors: ValidationErrors, is_update: bool = False):
    if hasattr(request, "title") and request.title is not None:
        if len(request.title.strip()) < 3:
            errors.add("title", "Title must be at least 3 characters")
    if hasattr(request, "location") and request.location is not None:
        if len(request.location.strip()) < 3:
            errors.add("location", "Location must be at least 3 characters")
    if hasattr(request, "max_capacity") and request.max_capacity is not None:
        if request.max_capacity <= 0:
            errors.add("max_capacity", "Capacity must be greater than 0")
        if request.max_capacity > 32767:
            errors.add("max_capacity", "Capacity cannot exceed 32767")
    if hasattr(request, "category") and request.category is not None:
        if len(request.category.strip()) < 2:
            errors.add("category", "Category must be at least 2 characters")


@router.get("", response_model=PaginatedResponse[EventResponse])
async def list_events(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    category: Optional[str] = None,
    is_active: Optional[bool] = True,
    db: AsyncSession = Depends(get_db),
):
    query = select(Event)

    if category:
        query = query.where(Event.category == category)
    if is_active is not None:
        query = query.where(Event.is_active == is_active)

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    query = query.offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    events = result.scalars().all()

    return PaginatedResponse(
        data=events,
        pagination=PaginationMeta(
            page=page,
            limit=limit,
            total=total,
            total_pages=(total + limit - 1) // limit,
        ),
    )


@router.post(
    "",
    response_model=EventResponse,
    status_code=status.HTTP_201_CREATED,
    responses={422: {"model": ValidationError}},
)
async def create_event(
    request: CreateEventRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    errors = ValidationErrors()
    validate_event_data(request, errors)

    if errors.has_errors():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=errors.to_response(),
        )

    new_event = Event(
        title=request.title,
        description=request.description,
        location=request.location,
        max_capacity=request.max_capacity,
        category=request.category,
    )

    db.add(new_event)
    await db.flush()
    await db.refresh(new_event)

    return new_event


@router.get("/{event_id}", response_model=EventResponse, responses={404: {"model": ValidationError}})
async def get_event(event_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=[{"field": "event_id", "message": "Event not found"}],
        )

    return event


@router.put(
    "/{event_id}",
    response_model=EventResponse,
    responses={404: {"model": ValidationError}, 422: {"model": ValidationError}},
)
async def update_event(
    event_id: UUID,
    request: UpdateEventRequest,
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
    validate_event_data(request, errors, is_update=True)

    if errors.has_errors():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=errors.to_response(),
        )

    update_data = request.model_dump(exclude_unset=True)
    for field_name, value in update_data.items():
        setattr(event, field_name, value)

    await db.flush()
    await db.refresh(event)

    return event


@router.delete(
    "/{event_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"model": ValidationError}},
)
async def delete_event(
    event_id: UUID,
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

    await db.delete(event)
    await db.flush()
