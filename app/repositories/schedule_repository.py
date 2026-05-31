from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from uuid import UUID
from datetime import date, time
from app.domain.models import EventSchedule
from app.repositories.base_repository import BaseRepository


class ScheduleRepository(BaseRepository[EventSchedule]):
    def __init__(self, db: AsyncSession):
        super().__init__(EventSchedule, db)

    async def get_by_event_id(self, event_id: UUID, start_date: date | None = None, end_date: date | None = None) -> list[EventSchedule]:
        query = select(EventSchedule).where(EventSchedule.event_id == event_id)
        if start_date:
            query = query.where(EventSchedule.schedule_date >= start_date)
        if end_date:
            query = query.where(EventSchedule.schedule_date <= end_date)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def find_conflicts(self, event_id: UUID, schedule_date: date, start_time: time, end_time: time, exclude_id: UUID | None = None) -> list[EventSchedule]:
        query = select(EventSchedule).where(
            and_(
                EventSchedule.event_id == event_id,
                EventSchedule.schedule_date == schedule_date,
                EventSchedule.start_time < end_time,
                EventSchedule.end_time > start_time,
            )
        )
        if exclude_id:
            query = query.where(EventSchedule.id != exclude_id)
        result = await self.db.execute(query)
        return result.scalars().all()
