from pathlib import Path
from typing import Optional

from pydantic import EmailStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# Абсолютный путь к .env в корне проекта (config.py -> core -> app -> корень),
# чтобы файл находился независимо от рабочего каталога при запуске.
ENV_FILE = Path(__file__).resolve().parent.parent.parent / '.env'


class Settings(BaseSettings):
    app_title: str = 'Благотворительный фонд поддержки котиков QRKot'
    description: str = 'Сервис для поддержки котиков'
    database_url: str = 'sqlite+aiosqlite:///./qrkot.db'
    secret: str = 'SECRET'
    first_superuser_email: Optional[EmailStr] = None
    first_superuser_password: Optional[str] = None
    model_config = SettingsConfigDict(env_file=ENV_FILE, extra='ignore')


settings = Settings()
