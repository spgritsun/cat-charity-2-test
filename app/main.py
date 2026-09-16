from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from app.api.routers import main_router
from app.core.config import settings

from app.core.init_db import create_first_superuser


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Всё, что указано выше yield, выполняется до запуска приложения.
    await create_first_superuser()

    # Lifespan-функция обязана вызывать yield,
    # но не должна возвращать никаких значений.
    yield

    # Все инструкции, описанные после yield,
    # выполняется перед завершением работы приложения.
    # В нашем случае ничего выполнять не нужно, но можно и пошалить:
    # print('И все эти мгновения исчезнут во времени, как слёзы под дождём.')


# Объект функции lifespan передаётся в аргумент lifespan объекта приложения.

app = FastAPI(title=settings.app_title, description=settings.description,
              lifespan=lifespan)
app.include_router(main_router)

if __name__ == "__main__":
    uvicorn.run('app.main:app', reload=True)
