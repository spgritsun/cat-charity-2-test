import contextlib

from fastapi_users.exceptions import UserAlreadyExists
from pydantic import EmailStr

from app.core.config import settings
from app.core.db import get_async_session
from app.core.user import get_user_db, get_user_manager
from app.schemas.user import UserCreate

# Превращаем асинхронные генераторы в асинхронные менеджеры контекста.
# Создаём менеджер контекста для получения сессий:
get_async_session_context = contextlib.asynccontextmanager(get_async_session)
# Создаём менеджер контекста для получения пользователя из базы:
get_user_db_context = contextlib.asynccontextmanager(get_user_db)
# Создаём менеджер контекста для получения объекта UserManager:
get_user_manager_context = contextlib.asynccontextmanager(get_user_manager)


# Корутина, создающая юзера с переданным email и паролем.
# Возможно создание суперюзера при передаче аргумента is_superuser=True.
async def create_user(
        email: EmailStr, password: str, is_superuser: bool = False
):
    try:
        # Получаем объект асинхронной сессии.
        async with get_async_session_context() as session:
            # Получаем объект класса SQLAlchemyUserDatabase.
            async with get_user_db_context(session) as user_db:
                # Получаем объект класса UserManager.
                async with get_user_manager_context(user_db) as user_manager:
                    # Создаём пользователя через метод create объекта
                    # UserManager.
                    await user_manager.create(
                        UserCreate(
                            email=email,
                            password=password,
                            is_superuser=is_superuser
                        )
                    )
    # Если пользователь с заданным email уже зарегистрирован в системе -
    # FastAPI Users выбросит исключение UserAlreadyExists. Обработаем эту
    # ошибку: если пользователь уже есть, ничего не предпринимать.
    except UserAlreadyExists:
        pass


# Корутина, проверяющая, указаны ли в настройках данные для суперюзера.
# Если да, то вызывается корутина create_user для создания суперпользователя.
async def create_first_superuser():
    if (settings.first_superuser_email is not None
            and settings.first_superuser_password is not None):
        await create_user(
            email=settings.first_superuser_email,
            password=settings.first_superuser_password,
            is_superuser=True,
        )
