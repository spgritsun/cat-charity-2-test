from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.donation import Donation


class CRUDDonation(CRUDBase[Donation]):

    async def get_my_donations(
            self,
            user_id: int,
            session: AsyncSession,
    ) -> Sequence[Donation]:
        db_objs = await session.execute(
            select(self.model).where(self.model.user_id == user_id)
        )
        return db_objs.scalars().all()


donation_crud = CRUDDonation(Donation)
