# Подсказки импортов из стандартной библиотеки
from typing import Annotated, Optional, Union

# Импорты типов из FastAPI
from fastapi import Depends, Request

# Необходимые импорты из fastapi-users
from fastapi_users import (
    BaseUserManager, FastAPIUsers, IntegerIDMixin, InvalidPasswordException
)
from fastapi_users.authentication import (
    AuthenticationBackend, BearerTransport, JWTStrategy
)
# Поскольку используется SQLAlchemy, импорт объекта из дополнительной
# библиотеки, поставляющейся с fastapi-users
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
# Импорт асинхронной сессии из SQLALchemy
from sqlalchemy.ext.asyncio import AsyncSession

# Импорты различных необходимых модулей из нашего собственного кода
from app.core.config import settings
from app.core.db import get_async_session
from app.models.user import User
from app.schemas.user import UserCreate


async def get_user_db(
        session: Annotated[AsyncSession, Depends(get_async_session)]
):
    yield SQLAlchemyUserDatabase(session, User)


# Определяем транспорт: передавать токен будем
# через заголовок HTTP-запроса Authorization: Bearer.
# Указываем URL эндпоинта для получения токена.
bearer_transport = BearerTransport(tokenUrl='auth/jwt/login')


# Определяем стратегию: хранение токена в виде JWT.
def get_jwt_strategy() -> JWTStrategy:
    # В специальный класс из настроек приложения
    # передаётся секретное слово, используемое для генерации токена.
    # Вторым аргументом передаём срок действия токена в секундах.
    return JWTStrategy(secret=settings.secret, lifetime_seconds=3600)


# Создаём объект бэкенда аутентификации с выбранными параметрами.
auth_backend = AuthenticationBackend(
    name='jwt',  # Произвольное имя бэкенда (должно быть уникальным).
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)


class UserManager(IntegerIDMixin, BaseUserManager[User, int]):

    # Здесь можно описать свои условия валидации пароля.
    # При успешной валидации функция ничего не возвращает.
    # При ошибке валидации будет вызван специальный класс ошибки
    # InvalidPasswordException.
    async def validate_password(
            self,
            password: str,
            user: Union[UserCreate, User],
    ) -> None:
        if len(password) < 3:
            error = 'Пароль должен содержать не менее 3 символов'
            raise InvalidPasswordException(
                reason=error
            )
        if user.email in password:
            error = 'Пароль не может содержать ваш email'
            raise InvalidPasswordException(
                reason=error
            )

    # Определяем метод, описывающий действия после успешной регистрации
    # пользователя.
    async def on_after_register(
            self, user: User, request: Optional[Request] = None
    ):
        # Вместо print здесь можно настроить отправку письма
        # или переадресацию пользователя на определённую страницу.
        print(f'Пользователь {user.email} зарегистрирован.')


# Корутина, возвращающая объект класса UserManager.
async def get_user_manager(user_db=Depends(get_user_db)):
    yield UserManager(user_db)


fastapi_users = FastAPIUsers[User, int](
    get_user_manager,
    [auth_backend],
)

current_user = fastapi_users.current_user(active=True)
current_superuser = fastapi_users.current_user(active=True, superuser=True)