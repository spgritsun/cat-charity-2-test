"""MCP-сервер для API фонда QRKot.

Даёт LLM (Claude Desktop, Claude Code, Cursor и др.) набор инструментов,
через которые модель работает с запущенным API: смотрит проекты, создаёт и
редактирует их, делает пожертвования и формирует отчёт.

Сервер сам ничего не хранит и не лезет в базу напрямую: он такой же клиент
API, как Postman или Swagger, просто управляет им модель. Поэтому модель
может ровно то, что разрешено учётной записи из переменных окружения.

Переменные окружения:
    QRKOT_URL       адрес API, по умолчанию http://127.0.0.1:8000
    QRKOT_EMAIL     email пользователя, от имени которого работает модель
    QRKOT_PASSWORD  его пароль

Запуск (обычно его запускает сам MCP-клиент):
    python mcp_server.py
"""
import asyncio
import os
from typing import Any, Optional

import httpx
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

API_URL = os.getenv('QRKOT_URL', 'http://127.0.0.1:8000').rstrip('/')
EMAIL = os.getenv('QRKOT_EMAIL')
PASSWORD = os.getenv('QRKOT_PASSWORD')
REQUEST_TIMEOUT = 60.0  # отчёт на Яндекс Диске может формироваться долго
# Для локального API не берём системный прокси Windows (VPN, прокси-программы):
# иначе запрос к 127.0.0.1 может уйти через прокси и не дойти до uvicorn.
USE_SYSTEM_PROXY = httpx.URL(API_URL).host not in (
    'localhost', '127.0.0.1', '::1')

# Подсказки для клиента: только чтение / безопасно повторять / опасно.
# Клиенты MCP используют их, например, чтобы спросить подтверждение.
READ_ONLY = {'readOnlyHint': True, 'idempotentHint': True}
WRITE = {'readOnlyHint': False, 'destructiveHint': False}
DESTRUCTIVE = {'readOnlyHint': False, 'destructiveHint': True}

mcp = FastMCP(
    name='QRKot',
    instructions=(
        'Инструменты фонда поддержки котиков QRKot. В фонде есть целевые '
        'проекты (сколько нужно собрать — full_amount, сколько собрано — '
        'invested_amount) и пожертвования. Деньги распределяются '
        'автоматически: новое пожертвование уходит в открытые проекты от '
        'старых к новым, новый проект сразу забирает свободные деньги. '
        'Проект закрывается (fully_invested=true), когда собрана вся сумма. '
        'Суммы — целые рубли. Перед удалением проекта или крупным '
        'пожертвованием уточни у пользователя, если он не сказал явно.'
    ),
)

_token: Optional[str] = None
_login_lock = asyncio.Lock()


async def _login(client: httpx.AsyncClient) -> str:
    """Получить JWT-токен по email и паролю."""
    if not EMAIL or not PASSWORD:
        raise ToolError(
            'Не заданы QRKOT_EMAIL и QRKOT_PASSWORD в настройках MCP-сервера.'
        )
    response = await client.post(
        '/auth/jwt/login', data={'username': EMAIL, 'password': PASSWORD}
    )
    if response.status_code != httpx.codes.OK:
        raise ToolError(
            f'Не удалось войти в QRKot под {EMAIL} '
            f'({_error_text(response)}). Проверьте email и пароль.'
        )
    return response.json()['access_token']


def _error_text(response: httpx.Response) -> str:
    """Достать понятный текст ошибки из ответа API."""
    try:
        detail = response.json().get('detail')
    except ValueError:
        detail = response.text
    if response.status_code == httpx.codes.UNAUTHORIZED:
        return 'Нужна авторизация (401).'
    if response.status_code == httpx.codes.FORBIDDEN:
        return ('Недостаточно прав (403): это действие доступно только '
                'суперпользователю.')
    if isinstance(detail, list):  # ошибки валидации от FastAPI (422)
        detail = '; '.join(
            f"{'.'.join(map(str, err.get('loc', [])[1:]))}: {err.get('msg')}"
            for err in detail
        )
    return f'Ошибка {response.status_code}: {detail}'


async def api(method: str, path: str, **kwargs) -> Any:
    """Выполнить запрос к API от имени пользователя.

    Токен берётся один раз и переиспользуется. Если он истёк (401),
    сервер один раз входит заново и повторяет запрос.
    Ошибки API превращаются в ToolError: модель увидит текст ошибки
    и сможет объяснить его пользователю или исправить запрос.
    """
    global _token
    async with httpx.AsyncClient(
            base_url=API_URL, timeout=REQUEST_TIMEOUT,
            trust_env=USE_SYSTEM_PROXY) as client:
        try:
            for attempt in range(2):
                async with _login_lock:
                    if _token is None:
                        _token = await _login(client)
                    token = _token
                response = await client.request(
                    method, path,
                    headers={'Authorization': f'Bearer {token}'},
                    **kwargs,
                )
                if (response.status_code == httpx.codes.UNAUTHORIZED
                        and attempt == 0):
                    _token = None
                    continue
                break
        except httpx.ConnectError:
            raise ToolError(
                f'API QRKot недоступен по адресу {API_URL}. '
                'Запущен ли uvicorn?'
            )
        except httpx.TimeoutException:
            raise ToolError('API QRKot не ответил вовремя.')
    if response.is_error:
        raise ToolError(_error_text(response))
    return response.json()


# ---------- Пользователь ----------

@mcp.tool(annotations=READ_ONLY)
async def whoami() -> dict:
    """Узнать, от имени какого пользователя работают инструменты и есть ли
    у него права суперпользователя (is_superuser)."""
    return await api('GET', '/users/me')


# ---------- Проекты ----------

@mcp.tool(annotations=READ_ONLY)
async def list_projects(only_open: bool = False) -> list[dict]:
    """Список благотворительных проектов.

    У каждого: id, name, description, full_amount (сколько нужно собрать),
    invested_amount (сколько уже собрано), fully_invested (закрыт ли),
    create_date, close_date.
    only_open=True — показать только проекты, где сбор ещё идёт.
    """
    projects = await api('GET', '/charity_project/')
    if only_open:
        projects = [p for p in projects if not p['fully_invested']]
    return projects


@mcp.tool(annotations=WRITE)
async def create_project(
        name: str, description: str, full_amount: int
) -> dict:
    """Создать новый проект (только суперпользователь).

    name — уникальное название, 5–100 символов;
    description — описание, не короче 10 символов;
    full_amount — сколько нужно собрать, целое число рублей больше 0.
    Свободные деньги из прошлых пожертвований сразу перейдут в проект.
    """
    return await api('POST', '/charity_project/', json={
        'name': name,
        'description': description,
        'full_amount': full_amount,
    })


@mcp.tool(annotations=WRITE)
async def update_project(
        project_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        full_amount: Optional[int] = None,
) -> dict:
    """Изменить проект (только суперпользователь).

    Передавай только те поля, которые нужно поменять. Закрытый проект
    менять нельзя; full_amount нельзя сделать меньше уже собранной суммы.
    Если новая full_amount равна собранной, проект закроется.
    """
    changes = {
        key: value for key, value in {
            'name': name,
            'description': description,
            'full_amount': full_amount,
        }.items() if value is not None
    }
    if not changes:
        raise ToolError('Не передано ни одного поля для изменения.')
    return await api('PATCH', f'/charity_project/{project_id}', json=changes)


@mcp.tool(annotations=DESTRUCTIVE)
async def delete_project(project_id: int) -> dict:
    """Удалить проект (только суперпользователь). Действие необратимо.

    Удалить можно только проект, в который ещё не поступило ни рубля.
    Перед вызовом убедись, что пользователь действительно хочет удаления.
    """
    return await api('DELETE', f'/charity_project/{project_id}')


# ---------- Пожертвования ----------

@mcp.tool(annotations=WRITE)
async def donate(full_amount: int, comment: Optional[str] = None) -> dict:
    """Сделать пожертвование от имени текущего пользователя.

    full_amount — сумма, целое число рублей больше 0; comment — необязательно.
    Конкретный проект выбрать нельзя: деньги сами распределятся по открытым
    проектам, начиная с самого старого. Пожертвование нельзя отменить.
    """
    payload = {'full_amount': full_amount}
    if comment:
        payload['comment'] = comment
    return await api('POST', '/donation/', json=payload)


@mcp.tool(annotations=READ_ONLY)
async def my_donations() -> list[dict]:
    """Пожертвования текущего пользователя: id, full_amount, comment,
    create_date."""
    return await api('GET', '/donation/my')


@mcp.tool(annotations=READ_ONLY)
async def all_donations() -> list[dict]:
    """Все пожертвования всех пользователей с информацией о распределении
    (только суперпользователь): user_id, full_amount, invested_amount,
    fully_invested и даты."""
    return await api('GET', '/donation/')


# ---------- Отчёт ----------

@mcp.tool(annotations=WRITE)
async def create_report() -> str:
    """Сформировать Excel-отчёт по закрытым проектам на Яндекс Диске
    (только суперпользователь). Проекты отсортированы по скорости сбора.
    Возвращает публичную ссылку на файл."""
    return await api('POST', '/yandex/')


if __name__ == '__main__':
    mcp.run()
