from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from app.api.routers import main_router
from app.core.config import settings
from app.core.init_db import create_first_superuser


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_first_superuser()
    yield


app = FastAPI(title=settings.app_title, description=settings.description,
              lifespan=lifespan)
app.include_router(main_router)

if __name__ == "__main__":
    uvicorn.run('app.main:app', reload=True)
