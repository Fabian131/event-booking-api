from uuid import UUID
from datetime import date
from fastapi import UploadFile
from app.core.validation import ValidationErrors
from app.core.cloudinary import upload_event_image, delete_event_image
from app.domain.models import Event
from app.repositories.event_repository import EventRepository
from app.schemas.event import CreateEventRequest, UpdateEventRequest, EventResponse


VALID_CATEGORIES = {"sports", "music", "culture", "gastronomy", "wellness", "education", "other"}


class EventValidator:
    @staticmethod
    def validate(request: CreateEventRequest | UpdateEventRequest, errors: ValidationErrors):
        if request.title is not None and len(request.title.strip()) < 3:
            errors.add("title", "Title must be at least 3 characters")
        if hasattr(request, 'end_time') and request.end_time is not None and hasattr(request, 'start_time') and request.start_time is not None:
            if request.end_time <= request.start_time:
                errors.add("end_time", "end_time must be after start_time")
        if hasattr(request, 'date') and request.date is not None:
            if request.date < date.today():
                errors.add("date", "Event date cannot be in the past")
        if request.max_capacity is not None:
            if request.max_capacity <= 0:
                errors.add("max_capacity", "Capacity must be greater than 0")
            elif request.max_capacity > 9999999:
                errors.add("max_capacity", "Capacity cannot exceed 9999999")


class EventService:
    def __init__(self, event_repo: EventRepository):
        self.event_repo = event_repo

    async def list_events(
        self,
        page: int,
        limit: int,
        category: str | None,
        is_active: bool | None,
        event_date: date | None = None,
        search: str | None = None,
    ) -> tuple[list[dict], int]:
        offset = (page - 1) * limit
        events = await self.event_repo.get_all_filtered(
            offset=offset, limit=limit, category=category,
            is_active=is_active, event_date=event_date, search=search,
        )
        total = await self.event_repo.count_filtered(
            category=category, is_active=is_active,
            event_date=event_date, search=search,
        )
        enriched = []
        for event in events:
            remaining = await self.event_repo.get_remaining_capacity(event.id)
            enriched.append(self._to_response(event, remaining))
        return enriched, total

    async def get_event(self, event_id: UUID) -> dict:
        event = await self.event_repo.get_by_id(event_id)
        if not event:
            raise ValueError([{"field": "event_id", "message": "Event not found"}])
        remaining = await self.event_repo.get_remaining_capacity(event.id)
        return self._to_response(event, remaining)

    async def create_event(self, request: CreateEventRequest, errors: ValidationErrors, image: UploadFile | None = None) -> dict:
        EventValidator.validate(request, errors)
        if errors.has_errors():
            raise ValueError(errors.to_response())

        conflicts = await self.event_repo.find_conflicts(
            request.date, request.start_time, request.end_time
        )
        if conflicts:
            raise ValueError([{"field": "schedule", "message": "An event already occupies this date and time slot"}])

        image_url = None
        if image:
            image_url = await upload_event_image(image)

        event = await self.event_repo.create(
            title=request.title,
            description=request.description,
            image_url=image_url,
            max_capacity=request.max_capacity,
            category=request.category.value,
            date=request.date,
            start_time=request.start_time,
            end_time=request.end_time,
        )
        return self._to_response(event, event.max_capacity)

    async def update_event(self, event_id: UUID, request: UpdateEventRequest, errors: ValidationErrors, image: UploadFile | None = None) -> dict:
        event = await self.event_repo.get_by_id(event_id)
        if not event:
            raise ValueError([{"field": "event_id", "message": "Event not found"}])

        EventValidator.validate(request, errors)
        if errors.has_errors():
            raise ValueError(errors.to_response())

        new_date = request.date or event.date
        new_start = request.start_time or event.start_time
        new_end = request.end_time or event.end_time

        if request.date or request.start_time or request.end_time:
            conflicts = await self.event_repo.find_conflicts(
                new_date, new_start, new_end, exclude_id=event_id
            )
            if conflicts:
                raise ValueError([{"field": "schedule", "message": "An event already occupies this date and time slot"}])

        update_data = request.model_dump(exclude_unset=True, exclude_none=True)
        if "category" in update_data and update_data["category"] is not None:
            update_data["category"] = update_data["category"].value

        if image:
            if event.image_url:
                delete_event_image(event.image_url)
            image_url = await upload_event_image(image)
            update_data["image_url"] = image_url

        updated = await self.event_repo.update(event, **update_data)
        remaining = await self.event_repo.get_remaining_capacity(updated.id)
        return self._to_response(updated, remaining)

    async def list_calendar_dates(self, year: int, month: int) -> list[dict]:
        return await self.event_repo.get_calendar_dates(year, month)

    async def delete_event(self, event_id: UUID) -> None:
        event = await self.event_repo.get_by_id(event_id)
        if not event:
            raise ValueError([{"field": "event_id", "message": "Event not found"}])
        await self.event_repo.delete(event)

    def _to_response(self, event: Event, remaining_capacity: int) -> dict:
        return {
            "id": event.id,
            "title": event.title,
            "description": event.description,
            "image_url": event.image_url,
            "max_capacity": event.max_capacity,
            "remaining_capacity": remaining_capacity,
            "category": event.category,
            "date": event.date,
            "start_time": event.start_time,
            "end_time": event.end_time,
            "is_active": event.is_active,
            "created_at": event.created_at,
            "updated_at": event.updated_at,
        }
