from uuid import UUID
from datetime import date
from app.core.validation import ValidationErrors
from app.domain.models import Reservation, Event
from app.repositories.reservation_repository import ReservationRepository
from app.repositories.event_repository import EventRepository
from app.repositories.notification_repository import NotificationRepository
from app.repositories.user_repository import UserRepository
from app.schemas.reservation import CreateReservationRequest, ReservationStatus, ReservationResponse, ReservationUserContext
from app.services.expo_push_service import expo_push_service


class ReservationService:
    def __init__(self, reservation_repo: ReservationRepository, event_repo: EventRepository, notification_repo: NotificationRepository, user_repo: UserRepository):
        self.reservation_repo = reservation_repo
        self.event_repo = event_repo
        self.notification_repo = notification_repo
        self.user_repo = user_repo

    async def list_reservations(
        self,
        user_id: UUID,
        user_role: str,
        page: int,
        limit: int,
        status_filter: str | None,
        event_id: UUID | None = None,
        search: str | None = None,
    ) -> tuple[list[dict], int]:
        offset = (page - 1) * limit

        if event_id and user_role == "business":
            reservations = await self.reservation_repo.get_by_event(
                event_id, offset, limit, status_filter, search
            )
            total = await self.reservation_repo.count_by_event(event_id, status_filter, search)
        else:
            reservations = await self.reservation_repo.get_by_user(user_id, offset, limit, status_filter)
            total = await self.reservation_repo.count_by_user(user_id, status_filter)

        enriched = []
        for r in reservations:
            enriched.append(await self._to_response(r))
        return enriched, total

    async def get_reservation(self, reservation_id: UUID, user_id: UUID, user_role: str) -> dict:
        reservation = await self.reservation_repo.get_by_id(reservation_id)
        if not reservation:
            raise ValueError([{"field": "reservation_id", "message": "Reservation not found"}])
        if user_role != "business" and reservation.user_id != user_id:
            raise ValueError([{"field": "reservation_id", "message": "Reservation not found"}])
        return await self._to_response(reservation)

    async def create_reservation(self, user_id: UUID, request: CreateReservationRequest, errors: ValidationErrors) -> dict:
        event = await self._get_event(request.event_id)

        if not event.is_active:
            errors.add("event_id", "Event is inactive")
        if event.date < date.today():
            errors.add("event_id", "Cannot reserve a past event")

        remaining = await self.event_repo.get_remaining_capacity(event.id)
        if remaining < request.ticket_quantity:
            errors.add("ticket_quantity", f"Only {remaining} slots available, requested {request.ticket_quantity}")

        if errors.has_errors():
            raise ValueError(errors.to_response())

        existing = await self.reservation_repo.get_by_user_and_event(
            user_id, request.event_id, ["CONFIRMED"]
        )
        if existing:
            raise ValueError([{"field": "event_id", "message": "You already have an active reservation for this event"}])

        reservation = await self.reservation_repo.create(
            user_id=user_id,
            event_id=request.event_id,
            ticket_quantity=request.ticket_quantity,
            notes=request.notes,
            status=ReservationStatus.CONFIRMED.value,
        )

        await self._notify(user_id, reservation, event, "reservation_confirmed", "Reservation Confirmed",
                           f"Your reservation for {event.title} has been confirmed.")
        return await self._to_response(reservation)

    async def cancel_reservation(self, reservation_id: UUID, user_id: UUID, user_role: str) -> dict:
        reservation = await self.reservation_repo.get_by_id(reservation_id)
        if not reservation:
            raise ValueError([{"field": "reservation_id", "message": "Reservation not found"}])
        if user_role != "business" and reservation.user_id != user_id:
            raise ValueError([{"field": "reservation_id", "message": "Reservation not found"}])

        if reservation.status == ReservationStatus.CANCELLED.value:
            raise ValueError([{"field": "status", "message": "This reservation has already been cancelled"}])

        reservation.status = ReservationStatus.CANCELLED.value
        await self.reservation_repo.update(reservation, status=reservation.status)

        event = await self.event_repo.get_by_id(reservation.event_id)
        await self._notify(reservation.user_id, reservation, event, "reservation_cancelled", "Reservation Cancelled",
                           f"Your reservation for {event.title} has been cancelled.")
        return await self._to_response(reservation)

    async def _get_event(self, event_id: UUID) -> Event:
        event = await self.event_repo.get_by_id(event_id)
        if not event:
            raise ValueError([{"field": "event_id", "message": "Event not found"}])
        return event

    async def _to_response(self, reservation: Reservation) -> dict:
        event = await self.event_repo.get_by_id(reservation.event_id)

        # Fetch user explicitly via async query to avoid lazy-load in async context
        user = None
        if self.user_repo:
            user = await self.user_repo.get_by_id(reservation.user_id)

        user_data = {
            "user_id": user.id if user else reservation.user_id,
            "user_name": f"{user.first_name} {user.last_name}" if user else "",
            "user_email": user.email if user else "",
        }

        return {
            "id": reservation.id,
            "user_id": reservation.user_id,
            "event_id": reservation.event_id,
            "event_title": event.title if event else "Unknown",
            "event_date": event.date if event else None,
            "event_start_time": event.start_time if event else None,
            "event_end_time": event.end_time if event else None,
            "ticket_quantity": reservation.ticket_quantity,
            "status": reservation.status,
            "notes": reservation.notes,
            "user": user_data,
            "created_at": reservation.created_at,
            "updated_at": reservation.updated_at,
        }

    async def _notify(self, user_id: UUID, reservation: Reservation, event: Event | None, ntype: str, title: str, message: str):
        await self.notification_repo.create_notification(
            user_id=user_id,
            notification_type=ntype,
            title=title,
            message=message,
            reservation_id=reservation.id,
            event_id=event.id if event else None,
        )

        user = await self.user_repo.get_by_id(user_id)
        if user and user.expo_push_token:
            await expo_push_service.send(
                to=user.expo_push_token,
                title=title,
                body=message,
                data={
                    "type": ntype,
                    "reservation_id": str(reservation.id),
                    "event_id": str(event.id) if event else None,
                },
            )
