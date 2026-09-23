from typing import Optional

import httpx
from fastapi import HTTPException, status

from app.core.config import settings


class YandexDiskClient:
    """Универсальный клиент для API Яндекс Диска"""
    FOLDER_NAME = "QRKot Reports"

    def __init__(self, token: str):
        self.token = token
        self.base_url = "https://cloud-api.yandex.net/v1/disk"
        self.headers = {"Authorization": f"OAuth {token}"}
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        self._client = httpx.AsyncClient(timeout=30.0)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()

    async def create_excel_file(self, title: str,
                                folder: str = FOLDER_NAME
                                ) -> tuple[str, str]:
        """
        Создаёт Excel-файл и возвращает ссылку для загрузки и путь к файлу
        """
        # Создаём папку, если её нет
        await self._create_folder(folder)

        file_path = f"disk:/{folder}/{title}.xlsx"

        # Получаем ссылку для загрузки
        response = await self._client.get(
            f"{self.base_url}/resources/upload",
            headers=self.headers,
            params={"path": file_path, "overwrite": "true"}
        )
        response.raise_for_status()

        data = response.json()
        upload_url = data.get("href")

        if not upload_url:
            raise ValueError("Не удалось получить ссылку для загрузки")

        return upload_url, file_path

    async def upload_file(self, upload_url: str, content: bytes):
        """Загружает файл по полученной ссылке"""
        response = await self._client.put(
            upload_url,
            content=content,
            headers={
                "Content-Type": "application/vnd.openxmlformats"
                                "-officedocument.spreadsheetml.sheet"}
        )
        response.raise_for_status()

    async def publish_file(self, file_path: str) -> str:
        """Делает файл публичным и возвращает ссылку"""
        # Публикуем файл
        response = await self._client.put(
            f"{self.base_url}/resources/publish",
            headers=self.headers,
            params={"path": file_path}
        )
        response.raise_for_status()

        # Получаем информацию о файле с публичной ссылкой
        response = await self._client.get(
            f"{self.base_url}/resources",
            headers=self.headers,
            params={"path": file_path}
        )
        response.raise_for_status()

        data = response.json()
        public_url = data.get("public_url")

        if not public_url:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Ссылка не была получена со стороны Яндекс Диска"
            )

        return public_url

    async def _create_folder(self, folder: str) -> None:
        """Создаёт папку, если её нет"""
        response = await self._client.put(
            f"{self.base_url}/resources",
            headers=self.headers,
            params={"path": f"disk:/{folder}"},
        )
        if response.status_code == status.HTTP_409_CONFLICT:
            return  # Папка уже существует
        response.raise_for_status()


async def get_yandex_client():
    """Dependency для получения клиента Яндекс Диска"""
    if not settings.yandex_disk_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Яндекс Диск не настроен. Пожалуйста, "
                   "добавьте YANDEX_DISK_TOKEN в .env-файл"
        )

    async with YandexDiskClient(settings.yandex_disk_token) as client:
        yield client
