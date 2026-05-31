from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.models import Event
from app.repositories.base_repository import BaseRepository


class EventRepository(BaseRepository[Event]):
    def __init__(self, db: AsyncSession):
        super().__init__(Event, db)
