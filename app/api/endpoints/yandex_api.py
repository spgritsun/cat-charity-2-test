from http import HTTPStatus

import httpx
from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import SessionDep
from app.core.user import current_superuser
from app.core.yandex_client import (YandexDiskClient, YandexDiskError,
                                    get_yandex_client)
from app.crud.charity_project import charity_project_crud
from app.services.yandex_api import create_simple_report

router = APIRouter()


@router.post(
    '/',
    response_model=str,
    dependencies=[Depends(current_superuser)],
    summary='Создать Excel-отчёт на Яндекс Диске',
)
async def create_report(
        session: SessionDep,
        yandex_client: YandexDiskClient = Depends(get_yandex_client)
) -> str:
    """Создать Excel-отчёт по закрытым проектам на Яндекс Диске.

    Проекты отсортированы по скорости сбора средств.
    Файл сохраняется на Яндекс Диске в папке 'QRKot Reports'
    и становится доступен по публичной ссылке.

    Требуются права суперпользователя.
    """
    projects_by_completion_rate = await (
        charity_project_crud.get_projects_by_completion_rate(session=session))

    if not projects_by_completion_rate:
        raise HTTPException(
            HTTPStatus.NOT_FOUND,
            detail='Нет данных для формирования отчёта'
        )

    try:
        public_url = await create_simple_report(yandex_client,
                                                projects_by_completion_rate)
        return public_url
    except (httpx.HTTPError, YandexDiskError) as e:
        raise HTTPException(
            HTTPStatus.INTERNAL_SERVER_ERROR,
            detail='Ошибка при создании отчёта'
        ) from e
