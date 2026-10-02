# MCP-сервер QRKot: управление фондом через LLM

`mcp_server.py` даёт языковой модели (Claude Desktop, Claude Code, Cursor
и другим MCP-клиентам) инструменты для работы с API QRKot. Вы пишете
обычным языком — «создай проект на 50 000 и пожертвуй в него 1000», —
а модель сама вызывает нужные эндпоинты.

```
Вы → Claude → mcp_server.py ── HTTP + JWT ──→ QRKot API (uvicorn) → база
```

MCP-сервер — такой же клиент API, как Postman: в базу он не лезет и может
ровно то, что разрешено учётной записи из настроек.

## Инструменты

| Инструмент       | Что делает                                   | Кому доступно   |
|------------------|----------------------------------------------|-----------------|
| `whoami`         | От чьего имени работает модель               | всем            |
| `list_projects`  | Список проектов (можно только открытые)      | всем            |
| `create_project` | Создать проект                               | суперюзер       |
| `update_project` | Изменить название, описание или сумму        | суперюзер       |
| `delete_project` | Удалить проект без вложений (помечен опасным)| суперюзер       |
| `donate`         | Сделать пожертвование                        | авторизованным  |
| `my_donations`   | Мои пожертвования                            | авторизованным  |
| `all_donations`  | Все пожертвования                            | суперюзер       |
| `create_report`  | Excel-отчёт на Яндекс Диске                  | суперюзер       |

Ошибки API (дубликат имени, закрытый проект, нет прав) возвращаются модели
текстом — она прочитает причину и объяснит её вам. Если токен истёк, сервер
сам войдёт заново.

## Установка (Windows)

MCP-серверу нужно **отдельное** окружение: FastMCP требует свежий pydantic,
а проект закреплён на старом. В папке проекта:

```bat
python -m venv venv-mcp
venv-mcp\Scripts\pip install -r requirements-mcp.txt
```

## Подключение к Claude Desktop

1. В Claude Desktop откройте **Settings → Developer → Edit Config**.
   Откроется файл `%APPDATA%\Claude\claude_desktop_config.json`.
2. Добавьте сервер (если в файле уже есть `mcpServers`, добавьте только
   блок `"qrkot"` внутрь него):

```json
{
  "mcpServers": {
    "qrkot": {
      "command": "C:\\cat-charity-2-test\\venv-mcp\\Scripts\\python.exe",
      "args": ["C:\\cat-charity-2-test\\mcp_server.py"],
      "env": {
        "QRKOT_URL": "http://127.0.0.1:8000",
        "QRKOT_EMAIL": "root@admin.ru",
        "QRKOT_PASSWORD": "root"
      }
    }
  }
}
```

3. Полностью закройте Claude Desktop (и из трея) и откройте снова.
4. Запустите сам API, иначе инструментам некуда обращаться:

```bat
venv\Scripts\activate
uvicorn app.main:app
```

Проверка: в окне чата нажмите «+» → Connectors — там должен появиться
`qrkot`. Спросите: «Кто я в QRKot и какие проекты ещё открыты?»

## Подключение к Claude Code

```bat
claude mcp add qrkot -e QRKOT_EMAIL=root@admin.ru -e QRKOT_PASSWORD=root -- C:\cat-charity-2-test\venv-mcp\Scripts\python.exe C:\cat-charity-2-test\mcp_server.py
```

## Безопасность

- **Права модели = права учётки из `env`.** Для пожертвований и просмотра
  хватит обычного пользователя. Суперпользователя давайте, только если
  модель должна управлять проектами.
- Пароль хранится в конфиге открытым текстом — используйте тестовую учётку,
  а не пароль от чего-то важного.
- `delete_project` помечен как разрушительный: клиент спросит подтверждение.
  Если удаление модели не нужно, просто уберите эту функцию из файла.

## Если не работает

- Логи Claude Desktop: `%APPDATA%\Claude\logs\mcp-server-qrkot.log`.
- «API QRKot недоступен» — не запущен uvicorn или неверный `QRKOT_URL`.
- «Не удалось войти» — неверные `QRKOT_EMAIL` / `QRKOT_PASSWORD`.
- `create_report` → «Яндекс Диск не настроен» — нет `YANDEX_DISK_TOKEN`
  в `.env` самого API.
