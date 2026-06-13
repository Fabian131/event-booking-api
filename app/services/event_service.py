import logging
from uuid import UUID
from datetime import date, datetime, timezone, timedelta

CR_TZ = timezone(timedelta(hours=-6))
from fastapi import UploadFile, BackgroundTasks
from app.core.validation import ValidationErrors
from app.core.cloudinary import upload_event_image, delete_event_image
from app.domain.models import Event
from app.repositories.event_repository import EventRepository
from app.repositories.reservation_repository import ReservationRepository
from app.services.email_service import email_service
from app.schemas.event import CreateEventRequest, UpdateEventRequest, EventResponse

logger = logging.getLogger(__name__)


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
            today_cr = datetime.now(CR_TZ).date()
            if request.date < today_cr:
                errors.add("date", "Event date cannot be in the past")
            elif request.date == today_cr and hasattr(request, 'start_time') and request.start_time is not None:
                now_cr = datetime.now(CR_TZ).time()
                if request.start_time <= now_cr:
                    errors.add("start_time", "Event start time cannot be in the past")
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

    async def delete_event(self, event_id: UUID, background_tasks: BackgroundTasks | None = None) -> None:
        event = await self.event_repo.get_by_id(event_id)
        if not event:
            raise ValueError([{"field": "event_id", "message": "Event not found"}])

        event_title = event.title
        event_date_str = event.date.isoformat()
        image_url = event.image_url

        recipients: list[dict] = []
        if background_tasks is not None:
            reservation_repo = ReservationRepository(self.event_repo.db)
            confirmed = await reservation_repo.get_confirmed_by_event(event_id, limit=1000)
            for reservation in confirmed:
                user = reservation.user
                if user and user.email:
                    recipients.append({
                        "email": user.email,
                        "name": f"{user.first_name} {user.last_name}",
                    })

        if image_url:
            from app.core.cloudinary import delete_event_image
            delete_event_image(image_url)

        await self.event_repo.delete(event)

        if background_tasks is not None:
            for recipient in recipients:
                background_tasks.add_task(
                    email_service.send_event_cancelled_email,
                    to_email=recipient["email"],
                    user_name=recipient["name"],
                    event_title=event_title,
                    event_date=event_date_str,
                )
                logger.info(
                    "Queued event cancellation email for %s regarding event %s",
                    recipient["email"], event_id,
                )
            if len(recipients) >= 1000:
                logger.warning(
                    "Event %s had >=1000 confirmed reservations. Only first 1000 were notified.",
                    event_id,
                )

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
