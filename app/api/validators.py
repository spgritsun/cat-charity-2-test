from http import HTTPStatus

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.constants import (FULL_AMOUNT_TOO_LOW, PROJECT_CLOSED,
                               PROJECT_HAS_INVESTMENTS,
                               PROJECT_NAME_DUPLICATE, PROJECT_NOT_FOUND)
from app.crud.charity_project import charity_project_crud
from app.models.charity_project import CharityProject
from app.schemas.charity_project import CharityProjectUpdate


async def check_name_duplicate(
        project_name: str,
        session: AsyncSession,
) -> None:
    project_id = await charity_project_crud.get_project_id_by_name(
        project_name, session)
    if project_id is not None:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=PROJECT_NAME_DUPLICATE,
        )


async def check_charity_project_exists(
        project_id: int,
        session: AsyncSession,
) -> CharityProject:
    charity_project = await charity_project_crud.get(project_id, session)
    if charity_project is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=PROJECT_NOT_FOUND,
        )
    return charity_project


def check_project_not_closed(
        charity_project: CharityProject
) -> None:
    if charity_project.fully_invested:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=PROJECT_CLOSED,
        )


def check_project_has_no_investments(
        charity_project: CharityProject
) -> None:
    if charity_project.invested_amount > 0:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=PROJECT_HAS_INVESTMENTS,
        )


def check_full_amount_not_less_invested(
        charity_project: CharityProject,
        obj_in: CharityProjectUpdate

) -> None:
    if (obj_in.full_amount is not None
            and obj_in.full_amount < charity_project.invested_amount):
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=FULL_AMOUNT_TOO_LOW,
        )
