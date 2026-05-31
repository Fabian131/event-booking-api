from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from app.domain.models import Reservation
from app.repositories.base_repository import BaseRepository


class ReservationRepository(BaseRepository[Reservation]):
    def __init__(self, db: AsyncSession):
        super().__init__(Reservation, db)

    async def get_by_user_and_schedule(self, user_id: UUID, schedule_id: UUID, statuses: list[str]) -> Reservation | None:
        result = await self.db.execute(
            select(Reservation).where(
                Reservation.user_id == user_id,
                Reservation.event_schedule_id == schedule_id,
                Reservation.status.in_(statuses),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_user(self, user_id: UUID, offset: int = 0, limit: int = 20, status_filter: str | None = None) -> list[Reservation]:
        query = select(Reservation).where(Reservation.user_id == user_id)
        if status_filter:
            query = query.where(Reservation.status == status_filter)
        query = query.offset(offset).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def count_by_user(self, user_id: UUID, status_filter: str | None = None) -> int:
        query = select(Reservation).where(Reservation.user_id == user_id)
        if status_filter:
            query = query.where(Reservation.status == status_filter)
        return await self.count()
