from uuid import UUID
from datetime import date, time
from app.core.validation import ValidationErrors
from app.domain.models import EventSchedule, Event
from app.repositories.schedule_repository import ScheduleRepository
from app.repositories.event_repository import EventRepository
from app.schemas.schedule import CreateEventScheduleRequest, UpdateEventScheduleRequest, AvailabilityResponse


class ScheduleValidator:
    @staticmethod
    def validate_times(schedule_date: date, start_time: time, end_time: time, errors: ValidationErrors):
        if end_time <= start_time:
            errors.add("end_time", "End time must be after start time")
        if schedule_date < date.today():
            errors.add("schedule_date", "Schedule date cannot be in the past")

    @staticmethod
    def validate_capacity(available_slots: int, max_capacity: int, errors: ValidationErrors):
        if available_slots > max_capacity:
            errors.add("available_slots", "Available slots cannot exceed event max capacity")


class ScheduleService:
    def __init__(self, schedule_repo: ScheduleRepository, event_repo: EventRepository):
        self.schedule_repo = schedule_repo
        self.event_repo = event_repo

    async def list_schedules(self, event_id: UUID, start_date: date | None, end_date: date | None) -> list[EventSchedule]:
        await self._ensure_event_exists(event_id)
        return await self.schedule_repo.get_by_event_id(event_id, start_date, end_date)

    async def get_schedule(self, schedule_id: UUID) -> EventSchedule:
        schedule = await self.schedule_repo.get_by_id(schedule_id)
        if not schedule:
            raise ValueError([{"field": "schedule_id", "message": "Schedule not found"}])
        return schedule

    async def create_schedule(self, event_id: UUID, request: CreateEventScheduleRequest, errors: ValidationErrors) -> EventSchedule:
        event = await self._ensure_event_exists(event_id)

        ScheduleValidator.validate_capacity(request.available_slots, event.max_capacity, errors)
        ScheduleValidator.validate_times(request.schedule_date, request.start_time, request.end_time, errors)

        if errors.has_errors():
            raise ValueError(errors.to_response())

        conflicts = await self.schedule_repo.find_conflicts(
            event_id, request.schedule_date, request.start_time, request.end_time
        )
        if conflicts:
            raise ValueError([{"field": "schedule", "message": "Schedule conflicts with existing schedule on this date and time range"}])

        return await self.schedule_repo.create(
            event_id=event_id,
            schedule_date=request.schedule_date,
            start_time=request.start_time,
            end_time=request.end_time,
            available_slots=request.available_slots,
        )

    async def update_schedule(self, schedule_id: UUID, request: UpdateEventScheduleRequest, errors: ValidationErrors) -> EventSchedule:
        schedule = await self.get_schedule(schedule_id)

        new_date = request.schedule_date or schedule.schedule_date
        new_start = request.start_time or schedule.start_time
        new_end = request.end_time or schedule.end_time

        ScheduleValidator.validate_times(new_date, new_start, new_end, errors)

        if request.available_slots is not None:
            event = await self.event_repo.get_by_id(schedule.event_id)
            ScheduleValidator.validate_capacity(request.available_slots, event.max_capacity, errors)

        if errors.has_errors():
            raise ValueError(errors.to_response())

        if request.schedule_date or request.start_time or request.end_time:
            conflicts = await self.schedule_repo.find_conflicts(
                schedule.event_id, new_date, new_start, new_end, exclude_id=schedule_id
            )
            if conflicts:
                raise ValueError([{"field": "schedule", "message": "Schedule conflicts with existing schedule"}])

        update_data = request.model_dump(exclude_unset=True)
        return await self.schedule_repo.update(schedule, **update_data)

    async def delete_schedule(self, schedule_id: UUID) -> None:
        schedule = await self.get_schedule()
        await self.schedule_repo.delete(schedule)

    async def check_availability(self, schedule_id: UUID) -> AvailabilityResponse:
        schedule = await self.get_schedule()
        event = await self.event_repo.get_by_id(schedule.event_id)

        return AvailabilityResponse(
            schedule_id=schedule.id,
            available_slots=schedule.available_slots,
            max_capacity=event.max_capacity,
            is_available=schedule.available_slots > 0,
        )

    async def _ensure_event_exists(self, event_id: UUID) -> Event:
        event = await self.event_repo.get_by_id(event_id)
        if not event:
            raise ValueError([{"field": "event_id", "message": "Event not found"}])
        return event
