from datetime import datetime
from typing import Optional

from sqlalchemy import CheckConstraint
from sqlalchemy.orm import declared_attr, Mapped, mapped_column

from app.core.db import Base, CommonMixin, utcnow


class CharityDonationBase(CommonMixin, Base):
    """Общие поля проекта и пожертвования."""

    __abstract__ = True

    full_amount: Mapped[int] = mapped_column(nullable=False)
    invested_amount: Mapped[int] = mapped_column(default=0, nullable=False)
    fully_invested: Mapped[bool] = mapped_column(default=False)
    create_date: Mapped[datetime] = mapped_column(default=utcnow)
    close_date: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    @declared_attr
    def __table_args__(cls):
        """Ограничения на уровне БД.

        `declared_attr` вызывается отдельно для каждого наследника, поэтому
        каждая таблица получает собственные объекты ограничений, связанные
        со своими колонками.
        """
        return (
            CheckConstraint(
                cls.full_amount > 0,
                name='full_amount_positive',
            ),
            CheckConstraint(
                cls.invested_amount.between(0, cls.full_amount),
                name='invested_amount_range',
            ),
        )
