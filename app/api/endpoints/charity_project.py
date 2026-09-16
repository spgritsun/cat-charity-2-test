from http import HTTPStatus

from fastapi import APIRouter, Depends

from app.api.constants import (FULL_AMOUNT_TOO_LOW,
                               INVALID_OPERATIONS_DESCRIPTION,
                               NOT_UNIQUE_NAME_DESCRIPTION, PROJECT_CLOSED,
                               PROJECT_HAS_INVESTMENTS,
                               PROJECT_NAME_DUPLICATE,
                               PROJECT_NOT_FOUND_DESCRIPTION,
                               PROJECT_UNDELETABLE_DESCRIPTION)
from app.api.deps import SessionDep
from app.api.responses import error_response
from app.api.validators import (check_charity_project_exists,
                                check_full_amount_not_less_invested,
                                check_name_duplicate,
                                check_project_has_no_investments,
                                check_project_not_closed)
from app.core.user import current_superuser
from app.crud.charity_project import charity_project_crud
from app.crud.donation import donation_crud
from app.schemas.charity_project import (CharityProjectCreate,
                                         CharityProjectDB,
                                         CharityProjectUpdate)
from app.services.investment import close_if_fully_invested, invest

router = APIRouter()

NOT_UNIQUE_NAME_EXAMPLE = {
    'notUniqueName': (NOT_UNIQUE_NAME_DESCRIPTION, PROJECT_NAME_DUPLICATE),
}
PROJECT_NOT_FOUND_RESPONSE = error_response(PROJECT_NOT_FOUND_DESCRIPTION)


@router.post(
    '/',
    response_model=CharityProjectDB,
    responses={
        HTTPStatus.BAD_REQUEST.value: error_response(
            NOT_UNIQUE_NAME_DESCRIPTION, NOT_UNIQUE_NAME_EXAMPLE
        ),
    },
    dependencies=[Depends(current_superuser)],
)
async def create_charity_project(
        charity_project: CharityProjectCreate,
        session: SessionDep,
):
    """Создать целевой проект."""
    await check_name_duplicate(charity_project.name, session)
    new_project = await charity_project_crud.create(
        charity_project.model_dump(), session
    )
    sources = await donation_crud.get_not_invested(session)
    session.add_all(invest(new_project, sources))
    await session.commit()
    return new_project


@router.get(
    '/',
    response_model=list[CharityProjectDB],
    response_model_exclude_none=True,
)
async def get_all_charity_projects(
        session: SessionDep,
):
    """Показать список всех целевых проектов."""
    all_projects = await charity_project_crud.get_multi(session)
    return all_projects


@router.patch(
    '/{project_id}',
    response_model=CharityProjectDB,
    response_model_exclude_none=True,
    responses={
        HTTPStatus.BAD_REQUEST.value: error_response(
            INVALID_OPERATIONS_DESCRIPTION,
            {
                'fullAmountTooLow': (
                    'Full amount lower than invested amount',
                    FULL_AMOUNT_TOO_LOW,
                ),
                **NOT_UNIQUE_NAME_EXAMPLE,
                'projectClosed': ('Project closed', PROJECT_CLOSED),
            },
        ),
        HTTPStatus.NOT_FOUND.value: PROJECT_NOT_FOUND_RESPONSE,
    },
    dependencies=[Depends(current_superuser)],
)
async def update_charity_project(
        project_id: int,
        obj_in: CharityProjectUpdate,
        session: SessionDep,
):
    """Редактировать целевой проект.

    Закрытый проект нельзя редактировать;
    нельзя установить требуемую сумму меньше уже вложенной.
    """
    charity_project = await check_charity_project_exists(
        project_id, session
    )
    check_project_not_closed(charity_project)
    if obj_in.name is not None:
        await check_name_duplicate(obj_in.name, session)
    check_full_amount_not_less_invested(charity_project, obj_in)
    charity_project = await charity_project_crud.update(
        charity_project, obj_in.model_dump(exclude_unset=True), session
    )
    close_if_fully_invested(charity_project)
    await session.commit()
    return charity_project


@router.delete(
    '/{project_id}',
    response_model=CharityProjectDB,
    response_model_exclude_none=True,
    responses={
        HTTPStatus.BAD_REQUEST.value: error_response(
            PROJECT_UNDELETABLE_DESCRIPTION,
            {
                'projectWithDonations': (
                    'Project closed or has donations',
                    PROJECT_HAS_INVESTMENTS,
                ),
            },
        ),
        HTTPStatus.NOT_FOUND.value: PROJECT_NOT_FOUND_RESPONSE,
    },
    dependencies=[Depends(current_superuser)],
)
async def delete_charity_project(
        project_id: int,
        session: SessionDep,
):
    """Удалить целевой проект.

    Нельзя удалить проект, в который уже были инвестированы средства.
    """
    charity_project = await check_charity_project_exists(project_id, session)
    check_project_has_no_investments(charity_project)
    charity_project = await charity_project_crud.remove(
        charity_project, session)
    await session.commit()
    return charity_project
