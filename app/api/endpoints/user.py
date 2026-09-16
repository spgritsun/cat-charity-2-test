# app/api/endpoints/user.py
from fastapi import APIRouter

from app.core.user import auth_backend, fastapi_users
from app.schemas.user import UserCreate, UserRead, UserUpdate

# Создаём новый роутер:
router = APIRouter()

# Подключаем роутер для аутентификации, импортированный из fastapi_users:
router.include_router(
    # В роутер аутентификации
    # должен быть передан объект бэкенда аутентификации.
    fastapi_users.get_auth_router(auth_backend),
    prefix='/auth/jwt',
    tags=['auth'],
)

# Подключаем роутер для регистрации, импортированный из fastapi_users:
router.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix='/auth',
    tags=['auth'],
)

users_router = fastapi_users.get_users_router(UserRead, UserUpdate)
users_router.routes = [
    # У каждого эндпоинта в библиотеке FastAPI User есть "личное имя",
    # оно устанавливается в параметре name эндпоинта.
    # По этому имени можно обратиться к эндпоинту или "идентифицировать" его.
    # Имя эндпоинта для удаления пользователей - 'users:delete_user'.
    # Заново переподключаем к роутеру все эндпоинты,
    # исключив эндпоинт для удаления пользователя.
    route for route in users_router.routes if route.name != 'users:delete_user'
]
# Подключаем изменённый роутер по старому адресу.
router.include_router(
    users_router,
    prefix='/users',
    tags=['users'],
)
