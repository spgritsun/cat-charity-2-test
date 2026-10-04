"""MCP-сервер для API фонда QRKot.

Даёт LLM (Claude Desktop, Claude Code, Cursor и др.) набор инструментов,
через которые модель работает с запущенным API: смотрит проекты, создаёт и
редактирует их, делает пожертвования и формирует отчёт.

Сервер сам ничего не хранит и не лезет в базу напрямую: он такой же клиент
API, как Postman или Swagger, просто управляет им модель. Поэтому модель
может ровно то, что разрешено учётной записи из переменных окружения.

Два режима работы (переменная MCP_TRANSPORT):

stdio (по умолчанию) — локальный режим. Сервер запускает сам MCP-клиент
    (например, Claude Desktop) и общается с ним через stdin/stdout.
    Сервер входит в API под учётной записью из QRKOT_EMAIL/QRKOT_PASSWORD.

http — режим для размещения в интернете. Сервер слушает порт и принимает
    подключения от любых агентов по адресу /mcp. Своей учётной записи у
    сервера НЕТ: каждый клиент присылает собственный JWT-токен QRKot в
    заголовке «Authorization: Bearer <токен>», и сервер пересылает его в
    API. Поэтому каждый агент может ровно то, что разрешено его учётке.
    QRKOT_EMAIL/QRKOT_PASSWORD в этом режиме игнорируются.

Переменные окружения:
    QRKOT_URL       адрес API, по умолчанию http://127.0.0.1:8000
    MCP_TRANSPORT   stdio (по умолчанию) или http
    QRKOT_EMAIL     только stdio: email пользователя, от имени которого
                    работает модель
    QRKOT_PASSWORD  только stdio: его пароль
    MCP_HOST        только http: адрес, по умолчанию 0.0.0.0
    MCP_PORT        только http: порт, по умолчанию 8000

Запуск:
    python mcp_server.py                      # stdio, обычно запускает клиент
    set MCP_TRANSPORT=http && python mcp_server.py   # http, Windows
"""
import asyncio
import os
from typing import Any, Optional

import httpx
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import get_http_headers
from starlette.requests import Request
from starlette.responses import PlainTextResponse

API_URL = os.getenv('QRKOT_URL', 'http://127.0.0.1:8000').rstrip('/')
TRANSPORT = os.getenv('MCP_TRANSPORT', 'stdio').lower()
if TRANSPORT not in ('stdio', 'http'):
    raise SystemExit('MCP_TRANSPORT должен быть stdio или http.')
IS_HTTP = TRANSPORT == 'http'
# В http-режиме учётные данные из окружения не используются вовсе:
# иначе любой, кто узнал адрес сервера, работал бы под этой учёткой.
EMAIL = None if IS_HTTP else os.getenv('QRKOT_EMAIL')
PASSWORD = None if IS_HTTP else os.getenv('QRKOT_PASSWORD')
HTTP_HOST = os.getenv('MCP_HOST', '0.0.0.0')
HTTP_PORT = int(os.getenv('MCP_PORT', '8000'))
BEARER_PREFIX = 'bearer '
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


def _client_token() -> str:
    """Достать JWT-токен клиента из заголовка Authorization (http-режим)."""
    header = get_http_headers(include={'authorization'}).get(
        'authorization', '')
    if not header.lower().startswith(BEARER_PREFIX):
        raise ToolError(
            'Нужен заголовок «Authorization: Bearer <токен>». Токен выдаёт '
            f'API QRKot: POST {API_URL}/auth/jwt/login.'
        )
    return header[len(BEARER_PREFIX):].strip()


async def _client_api(
        client: httpx.AsyncClient, method: str, path: str, **kwargs
) -> httpx.Response:
    """Запрос с токеном клиента (http-режим).

    Сервер не может сам войти заново, потому что не знает пароля клиента:
    при истёкшем токене просто объясняем, что делать.
    """
    response = await client.request(
        method, path,
        headers={'Authorization': f'Bearer {_client_token()}'},
        **kwargs,
    )
    if response.status_code == httpx.codes.UNAUTHORIZED:
        raise ToolError(
            'Токен недействителен или истёк (401). Получите новый: '
            f'POST {API_URL}/auth/jwt/login, и переподключитесь.'
        )
    return response


async def _own_api(
        client: httpx.AsyncClient, method: str, path: str, **kwargs
) -> httpx.Response:
    """Запрос под учётной записью из окружения (stdio-режим).

    Токен берётся один раз и переиспользуется. Если он истёк (401),
    сервер один раз входит заново и повторяет запрос.
    """
    global _token
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
    return response


async def api(method: str, path: str, **kwargs) -> Any:
    """Выполнить запрос к API от имени пользователя.

    В http-режиме — с токеном клиента, в stdio — под учёткой из окружения.
    Ошибки API превращаются в ToolError: модель увидит текст ошибки
    и сможет объяснить его пользователю или исправить запрос.
    """
    send = _client_api if IS_HTTP else _own_api
    async with httpx.AsyncClient(
            base_url=API_URL, timeout=REQUEST_TIMEOUT,
            trust_env=USE_SYSTEM_PROXY) as client:
        try:
            response = await send(client, method, path, **kwargs)
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


# ---------- Служебное ----------

@mcp.custom_route('/health', methods=['GET'])
async def health(request: Request) -> PlainTextResponse:
    """Проверка состояния для хостинга (http-режим): сервер жив."""
    return PlainTextResponse('OK')


if __name__ == '__main__':
    if IS_HTTP:
        # stateless_http: каждый запрос самодостаточен, сервер не хранит
        # сессии в памяти — переживает перезапуск контейнера.
        mcp.run(transport='http', host=HTTP_HOST, port=HTTP_PORT,
                stateless_http=True)
    else:
        mcp.run()
