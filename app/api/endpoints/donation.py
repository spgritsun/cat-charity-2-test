from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import SessionDep
from app.core.user import current_user
from app.crud.charity_project import charity_project_crud
from app.crud.donation import donation_crud
from app.models import User
from app.schemas.donation import DonationCreate, DonationDB, DonationFullInfoDB
from app.services.investment import invest

router = APIRouter()


@router.post(
    '/',
    response_model=DonationDB,
    response_model_exclude_none=True,
)
async def create_donation(
        donation: DonationCreate,
        session: SessionDep,
        user: Annotated[User, Depends(current_user)]
):
    """Создать пожертвование."""
    new_donation = await donation_crud.create({**donation.model_dump(),
                                               'user_id': user.id}, session)
    sources = await charity_project_crud.get_not_invested(session)
    session.add_all(invest(new_donation, sources))
    await session.commit()
    return new_donation


@router.get(
    '/',
    response_model=list[DonationFullInfoDB],
    response_model_exclude_none=True,
)
async def get_all_donations(
        session: SessionDep,
):
    """Показать список всех пожертвований."""
    donations = await donation_crud.get_multi(session)
    return donations
