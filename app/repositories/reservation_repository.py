from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from app.domain.models import Reservation, User
from app.repositories.base_repository import BaseRepository


class ReservationRepository(BaseRepository[Reservation]):
    def __init__(self, db: AsyncSession):
        super().__init__(Reservation, db)

    async def get_by_id(self, reservation_id: UUID) -> Reservation | None:
        result = await self.db.execute(
            select(Reservation).options(selectinload(Reservation.user)).where(Reservation.id == reservation_id)
        )
        return result.scalar_one_or_none()

    async def get_by_user_and_event(self, user_id: UUID, event_id: UUID, statuses: list[str]) -> Reservation | None:
        result = await self.db.execute(
            select(Reservation).where(
                Reservation.user_id == user_id,
                Reservation.event_id == event_id,
                Reservation.status.in_(statuses),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_user(self, user_id: UUID, offset: int = 0, limit: int = 20, status_filter: str | None = None) -> list[Reservation]:
        query = select(Reservation).options(selectinload(Reservation.user)).where(Reservation.user_id == user_id)
        if status_filter:
            query = query.where(Reservation.status == status_filter)
        query = query.order_by(Reservation.created_at.desc())
        query = query.offset(offset).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def count_by_user(self, user_id: UUID, status_filter: str | None = None) -> int:
        query = select(func.count()).select_from(Reservation).where(Reservation.user_id == user_id)
        if status_filter:
            query = query.where(Reservation.status == status_filter)
        result = await self.db.execute(query)
        return result.scalar()

    async def get_by_event(
        self,
        event_id: UUID,
        offset: int = 0,
        limit: int = 20,
        status_filter: str | None = None,
        search: str | None = None,
    ) -> list[Reservation]:
        query = select(Reservation).options(selectinload(Reservation.user)).join(User, Reservation.user_id == User.id).where(Reservation.event_id == event_id)
        if status_filter:
            query = query.where(Reservation.status == status_filter)
        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                or_(
                    User.first_name.ilike(search_pattern),
                    User.last_name.ilike(search_pattern),
                    User.email.ilike(search_pattern),
                )
            )
        query = query.order_by(Reservation.created_at.desc())
        query = query.offset(offset).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def count_by_event(self, event_id: UUID, status_filter: str | None = None, search: str | None = None) -> int:
        query = select(func.count()).select_from(Reservation).join(User, Reservation.user_id == User.id).where(Reservation.event_id == event_id)
        if status_filter:
            query = query.where(Reservation.status == status_filter)
        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                or_(
                    User.first_name.ilike(search_pattern),
                    User.last_name.ilike(search_pattern),
                    User.email.ilike(search_pattern),
                )
            )
        result = await self.db.execute(query)
        return result.scalar()

    async def get_confirmed_by_event(self, event_id: UUID, limit: int | None = None) -> list[Reservation]:
        query = (
            select(Reservation)
            .options(selectinload(Reservation.user))
            .where(
                Reservation.event_id == event_id,
                Reservation.status == "CONFIRMED",
            )
        )
        if limit is not None:
            query = query.limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def sum_booked_tickets(self, event_id: UUID) -> int:
        query = select(func.coalesce(func.sum(Reservation.ticket_quantity), 0)).where(
            and_(
                Reservation.event_id == event_id,
                Reservation.status == "CONFIRMED",
            )
        )
        result = await self.db.execute(query)
        return result.scalar()
