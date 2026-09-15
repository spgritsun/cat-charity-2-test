from datetime import datetime, timezone

from sqlalchemy import Integer
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import (DeclarativeBase, declared_attr, Mapped,
                            mapped_column)

from app.core.config import settings


class Base(DeclarativeBase):
    pass


class CommonMixin:

    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

    id: Mapped[int] = mapped_column(Integer, primary_key=True)


engine = create_async_engine(settings.database_url)

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def get_async_session():
    async with AsyncSessionLocal() as async_session:
        yield async_session
