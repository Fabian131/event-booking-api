from typing import Generic, TypeVar, Type, Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    def __init__(self, model: Type[ModelType], db: AsyncSession):
        self.model = model
        self.db = db

    async def get_by_id(self, id: UUID) -> Optional[ModelType]:
        result = await self.db.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()

    async def get_all(self, offset: int = 0, limit: int = 20, **filters) -> List[ModelType]:
        query = select(self.model)
        for field, value in filters.items():
            if value is not None:
                query = query.where(getattr(self.model, field) == value)
        query = query.offset(offset).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def count(self, **filters) -> int:
        query = select(func.count()).select_from(self.model)
        for field, value in filters.items():
            if value is not None:
                query = query.where(getattr(self.model, field) == value)
        result = await self.db.execute(query)
        return result.scalar()

    async def create(self, **kwargs) -> ModelType:
        instance = self.model(**kwargs)
        self.db.add(instance)
        await self.db.flush()
        await self.db.refresh(instance)
        return instance

    async def update(self, instance: ModelType, **kwargs) -> ModelType:
        for field, value in kwargs.items():
            setattr(instance, field, value)
        await self.db.flush()
        await self.db.refresh(instance)
        return instance

    async def delete(self, instance: ModelType) -> None:
        await self.db.delete(instance)
        await self.db.flush()
