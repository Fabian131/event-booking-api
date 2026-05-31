from uuid import UUID
from datetime import date
from app.core.validation import ValidationErrors
from app.domain.models import Reservation, EventSchedule
from app.repositories.reservation_repository import ReservationRepository
from app.repositories.schedule_repository import ScheduleRepository
from app.repositories.notification_repository import NotificationRepository
from app.schemas.reservation import CreateReservationRequest, ReservationStatus


class ReservationValidator:
    @staticmethod
    def validate_schedule_date(schedule_date: date, errors: ValidationErrors):
        if schedule_date < date.today():
            errors.add("event_schedule_id", "Cannot reserve a past schedule")

    @staticmethod
    def validate_availability(available_slots: int, requested_quantity: int, errors: ValidationErrors):
        if available_slots < requested_quantity:
            errors.add("quantity", f"Only {available_slots} slots available, requested {requested_quantity}")


class ReservationService:
    def __init__(self, reservation_repo: ReservationRepository, schedule_repo: ScheduleRepository, notification_repo: NotificationRepository):
        self.reservation_repo = reservation_repo
        self.schedule_repo = schedule_repo
        self.notification_repo = notification_repo

    async def list_reservations(self, user_id: UUID, page: int, limit: int, status_filter: str | None) -> tuple[list[Reservation], int]:
        offset = (page - 1) * limit
        reservations = await self.reservation_repo.get_by_user(user_id, offset, limit, status_filter)
        total = await self.reservation_repo.count_by_user(user_id, status_filter)
        return reservations, total

    async def get_reservation(self, reservation_id: UUID, user_id: UUID) -> Reservation:
        reservation = await self.reservation_repo.get_by_id(reservation_id)
        if not reservation or reservation.user_id != user_id:
            raise ValueError([{"field": "reservation_id", "message": "Reservation not found"}])
        return reservation

    async def create_reservation(self, user_id: UUID, request: CreateReservationRequest, errors: ValidationErrors) -> Reservation:
        schedule = await self._get_schedule(request.event_schedule_id)

        ReservationValidator.validate_schedule_date(schedule.schedule_date, errors)
        ReservationValidator.validate_availability(schedule.available_slots, request.quantity, errors)

        if errors.has_errors():
            raise ValueError(errors.to_response())

        existing = await self.reservation_repo.get_by_user_and_schedule(
            user_id, request.event_schedule_id, ["PENDING", "CONFIRMED"]
        )
        if existing:
            raise ValueError([{"field": "event_schedule_id", "message": "You already have an active reservation for this schedule"}])

        schedule.available_slots -= request.quantity

        reservation = await self.reservation_repo.create(
            user_id=user_id,
            event_schedule_id=request.event_schedule_id,
            quantity=request.quantity,
            notes=request.notes,
            status=ReservationStatus.PENDING.value,
        )

        await self._notify_reservation_created(user_id, reservation)
        return reservation

    async def confirm_reservation(self, reservation_id: UUID, user_id: UUID) -> Reservation:
        reservation = await self.get_reservation(reservation_id, user_id)

        if reservation.status == ReservationStatus.CONFIRMED.value:
            raise ValueError([{"field": "status", "message": "Reservation is already confirmed"}])
        if reservation.status == ReservationStatus.CANCELLED.value:
            raise ValueError([{"field": "status", "message": "Cannot confirm a cancelled reservation"}])

        reservation.status = ReservationStatus.CONFIRMED.value
        await self.reservation_repo.update(reservation, status=reservation.status)

        await self._notify_reservation_confirmed(user_id, reservation)
        return reservation

    async def cancel_reservation(self, reservation_id: UUID, user_id: UUID) -> Reservation:
        reservation = await self.get_reservation(reservation_id, user_id)

        if reservation.status == ReservationStatus.CANCELLED.value:
            raise ValueError([{"field": "status", "message": "Reservation is already cancelled"}])

        schedule = await self._get_schedule(reservation.event_schedule_id)
        schedule.available_slots += reservation.quantity

        reservation.status = ReservationStatus.CANCELLED.value
        await self.reservation_repo.update(reservation, status=reservation.status)

        await self._notify_reservation_cancelled(user_id, reservation)
        return reservation

    async def _get_schedule(self, schedule_id: UUID) -> EventSchedule:
        schedule = await self.schedule_repo.get_by_id(schedule_id)
        if not schedule:
            raise ValueError([{"field": "event_schedule_id", "message": "Schedule not found"}])
        return schedule

    async def _notify_reservation_created(self, user_id: UUID, reservation: Reservation):
        await self.notification_repo.create_notification(
            user_id=user_id,
            notification_type="RESERVATION_CREATED",
            title="Reservation Created",
            message=f"Your reservation for {reservation.quantity} slot(s) has been created.",
            reservation_id=reservation.id,
        )

    async def _notify_reservation_confirmed(self, user_id: UUID, reservation: Reservation):
        await self.notification_repo.create_notification(
            user_id=user_id,
            notification_type="RESERVATION_CONFIRMED",
            title="Reservation Confirmed",
            message=f"Your reservation has been confirmed.",
            reservation_id=reservation.id,
        )

    async def _notify_reservation_cancelled(self, user_id: UUID, reservation: Reservation):
        await self.notification_repo.create_notification(
            user_id=user_id,
            notification_type="RESERVATION_CANCELLED",
            title="Reservation Cancelled",
            message=f"Your reservation has been cancelled. Slots have been restored.",
            reservation_id=reservation.id,
        )
