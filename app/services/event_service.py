from uuid import UUID
from app.core.validation import ValidationErrors
from app.domain.models import Event
from app.repositories.event_repository import EventRepository
from app.schemas.event import CreateEventRequest, UpdateEventRequest


class EventValidator:
    @staticmethod
    def validate(request: CreateEventRequest | UpdateEventRequest, errors: ValidationErrors):
        if request.title is not None and len(request.title.strip()) < 3:
            errors.add("title", "Title must be at least 3 characters")
        if request.location is not None and len(request.location.strip()) < 3:
            errors.add("location", "Location must be at least 3 characters")
        if request.max_capacity is not None:
            if request.max_capacity <= 0:
                errors.add("max_capacity", "Capacity must be greater than 0")
            elif request.max_capacity > 32767:
                errors.add("max_capacity", "Capacity cannot exceed 32767")
        if request.category is not None and len(request.category.strip()) < 2:
            errors.add("category", "Category must be at least 2 characters")


class EventService:
    def __init__(self, event_repo: EventRepository):
        self.event_repo = event_repo

    async def list_events(self, page: int, limit: int, category: str | None, is_active: bool | None) -> tuple[list[Event], int]:
        offset = (page - 1) * limit
        events = await self.event_repo.get_all(offset=offset, limit=limit, category=category, is_active=is_active)
        total = await self.event_repo.count(category=category, is_active=is_active)
        return events, total

    async def get_event(self, event_id: UUID) -> Event:
        event = await self.event_repo.get_by_id(event_id)
        if not event:
            raise ValueError([{"field": "event_id", "message": "Event not found"}])
        return event

    async def create_event(self, request: CreateEventRequest, errors: ValidationErrors) -> Event:
        EventValidator.validate(request, errors)
        if errors.has_errors():
            raise ValueError(errors.to_response())

        return await self.event_repo.create(
            title=request.title,
            description=request.description,
            location=request.location,
            max_capacity=request.max_capacity,
            category=request.category,
        )

    async def update_event(self, event_id: UUID, request: UpdateEventRequest, errors: ValidationErrors) -> Event:
        event = await self.get_event(event_id)

        EventValidator.validate(request, errors)
        if errors.has_errors():
            raise ValueError(errors.to_response())

        update_data = request.model_dump(exclude_unset=True)
        return await self.event_repo.update(event, **update_data)

    async def delete_event(self, event_id: UUID) -> None:
        event = await self.get_event(event_id)
        await self.event_repo.delete(event)
