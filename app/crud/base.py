from collections.abc import Sequence
from typing import Generic, Optional, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import Base

ModelType = TypeVar('ModelType', bound=Base)


class CRUDBase(Generic[ModelType]):
    def __init__(self, model: type[ModelType]) -> None:
        self.model = model

    async def get(
            self,
            obj_id: int,
            session: AsyncSession,
    ) -> Optional[ModelType]:
        db_obj = await session.execute(
            select(self.model).where(
                self.model.id == obj_id
            )
        )
        return db_obj.scalars().first()

    async def get_multi(
            self,
            session: AsyncSession
    ) -> Sequence[ModelType]:
        db_objs = await session.execute(select(self.model))
        return db_objs.scalars().all()

    async def create(
            self,
            obj_in_data: dict,
            session: AsyncSession,
    ) -> ModelType:
        """Добавить объект в сессию без коммита.

        `flush()` отправляет INSERT в БД и заполняет автогенерируемые поля
        (например, `id`), но оставляет транзакцию открытой: вызывающий код
        сам решает, когда её завершить.
        """
        db_obj = self.model(**obj_in_data)
        session.add(db_obj)
        await session.flush()
        return db_obj

    async def update(
            self,
            db_obj: ModelType,
            update_data: dict,
            session: AsyncSession,
    ) -> ModelType:
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        session.add(db_obj)
        return db_obj

    async def remove(
            self,
            db_obj: ModelType,
            session: AsyncSession,
    ) -> ModelType:
        await session.delete(db_obj)
        return db_obj

    async def get_not_invested(
            self,
            session: AsyncSession,
    ) -> Sequence[ModelType]:
        db_objs = await session.execute(
            select(self.model).where(
                self.model.fully_invested.is_(False)
            ).order_by(self.model.create_date)
        )
        return db_objs.scalars().all()
