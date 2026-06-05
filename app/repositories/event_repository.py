from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, extract
from uuid import UUID
from datetime import date, time
from app.domain.models import Event, Reservation
from app.repositories.base_repository import BaseRepository


class EventRepository(BaseRepository[Event]):
    def __init__(self, db: AsyncSession):
        super().__init__(Event, db)

    async def get_all_filtered(
        self,
        offset: int = 0,
        limit: int = 20,
        category: str | None = None,
        is_active: bool | None = True,
        event_date: date | None = None,
        search: str | None = None,
    ) -> list[Event]:
        query = select(Event)
        if is_active is not None:
            query = query.where(Event.is_active == is_active)
        if category:
            query = query.where(Event.category == category)
        if event_date:
            query = query.where(Event.date == event_date)
        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                or_(
                    Event.title.ilike(search_pattern),
                    Event.description.ilike(search_pattern),
                )
            )
        query = query.order_by(Event.date.desc(), Event.start_time.asc())
        query = query.offset(offset).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def count_filtered(
        self,
        category: str | None = None,
        is_active: bool | None = True,
        event_date: date | None = None,
        search: str | None = None,
    ) -> int:
        query = select(func.count()).select_from(Event)
        if is_active is not None:
            query = query.where(Event.is_active == is_active)
        if category:
            query = query.where(Event.category == category)
        if event_date:
            query = query.where(Event.date == event_date)
        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                or_(
                    Event.title.ilike(search_pattern),
                    Event.description.ilike(search_pattern),
                )
            )
        result = await self.db.execute(query)
        return result.scalar()

    async def find_conflicts(
        self,
        event_date: date,
        start_time: time,
        end_time: time,
        exclude_id: UUID | None = None,
    ) -> list[Event]:
        query = select(Event).where(
            and_(
                Event.date == event_date,
                Event.start_time < end_time,
                Event.end_time > start_time,
            )
        )
        if exclude_id:
            query = query.where(Event.id != exclude_id)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_remaining_capacity(self, event_id: UUID) -> int:
        """Calculate remaining_capacity = max_capacity - sum(ticket_quantity) of active reservations."""
        event = await self.get_by_id(event_id)
        if not event:
            return 0
        query = select(func.coalesce(func.sum(Reservation.ticket_quantity), 0)).where(
            and_(
                Reservation.event_id == event_id,
                Reservation.status.in_(["PENDING", "CONFIRMED"]),
            )
        )
        result = await self.db.execute(query)
        booked = result.scalar()
        return event.max_capacity - booked

    async def get_calendar_dates(self, year: int, month: int) -> list[dict]:
        query = (
            select(Event.date, func.count(Event.id).label("count"))
            .where(
                extract("year", Event.date) == year,
                extract("month", Event.date) == month,
                Event.is_active == True,
            )
            .group_by(Event.date)
            .order_by(Event.date.asc())
        )
        result = await self.db.execute(query)
        return [{"date": row.date, "count": row.count} for row in result.all()]
