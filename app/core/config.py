from pathlib import Path
from typing import Optional

from pydantic import EmailStr, PositiveInt
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parent.parent.parent / '.env'


class Settings(BaseSettings):
    app_title: str = 'Благотворительный фонд поддержки котиков QRKot'
    description: str = 'Сервис для поддержки котиков'
    database_url: str = 'sqlite+aiosqlite:///./qrkot.db'
    secret: str = 'SECRET'
    jwt_lifetime_seconds: PositiveInt = 3600
    first_superuser_email: Optional[EmailStr] = None
    first_superuser_password: Optional[str] = None
    yandex_disk_token: Optional[str] = None
    report_format: str = "%d.%m.%Y_%H-%M-%S"
    model_config = SettingsConfigDict(env_file=ENV_FILE, extra='ignore')


settings = Settings()
