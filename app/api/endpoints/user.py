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

# Подключаем роутер для управления пользователями, импортированный из
# fastapi_users:
router.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix='/users',
    tags=['users'],
)
