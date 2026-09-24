# ...app/services/yandex_api.py
import io
from datetime import datetime, timedelta
from typing import List, Dict, Any

import xlsxwriter

from app.core.config import settings
from app.core.yandex_client import YandexDiskClient


def format_time_delta(delta: timedelta) -> str:
    """Форматирует timedelta в строку 'X дн. Y ч.' или 'Y ч. Z мин.'."""
    days = delta.days
    hours, remainder = divmod(delta.seconds, 3600)
    minutes = remainder // 60
    if days:
        return f'{days} дн. {hours} ч.'
    return f'{hours} ч. {minutes} мин.'


async def set_user_permissions(
        file_path: str,
        yandex_client: YandexDiskClient
) -> str:
    """
    Делает файл публичным и возвращает ссылку
    (аналог set_user_permissions из Google-версии)
    """
    return await yandex_client.publish_file(file_path)


async def spreadsheets_create(
        yandex_client: YandexDiskClient,
        folder: str = "Reports"
) -> tuple[str, str]:
    """
    Создаёт Excel-файл и возвращает upload_url и file_path
    (аналог spreadsheets_create из Google-версии)
    """
    now_date_time = datetime.now().strftime(settings.report_format)
    safe_filename = (f"Отчет_{now_date_time}".replace(':', '-')
                     .replace(' ', '_').replace('/', '-'))

    upload_url, file_path = await yandex_client.create_spreadsheet(
        safe_filename, folder)
    return upload_url, file_path


async def spreadsheets_update_value(
        upload_url: str,
        reservations: List[Dict[str, Any]],
        yandex_client: YandexDiskClient
) -> None:
    """
    Записывает данные в Excel-файл и загружает на Яндекс Диск
    """
    now_date_time = datetime.now().strftime(settings.report_format)

    # Создаём Excel-файл в памяти
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output)
    worksheet = workbook.add_worksheet("Отчет")

    # Форматы
    title_format = workbook.add_format({'bold': True, 'font_size': 14})
    header_format = workbook.add_format({
        'bold': True,
        'bg_color': '#2F75B5',
        'font_color': 'white',
        'border': 1,
        'align': 'center'
    })
    cell_format = workbook.add_format({'border': 1, 'align': 'center'})

    # Заголовок отчёта
    worksheet.merge_range('A1:B1', f"Отчет от {now_date_time}", title_format)

    # Объединённый заголовок "Количество регистраций переговорок" (A2:B2)
    worksheet.merge_range('A2:B2', "Количество регистраций переговорок",
                          header_format)

    # Заголовки колонок (строка 3)
    headers = ['ID переговорки', 'Кол-во бронирований']
    for col, header in enumerate(headers):
        worksheet.write(2, col, header, header_format)  # Строка 3 (индекс 2)

    # Данные (начиная с 4-й строки)
    for row, res in enumerate(reservations, start=3):
        worksheet.write(row, 0, str(res['meetingroom_id']), cell_format)
        worksheet.write(row, 1, str(res['count']), cell_format)

    # Настраиваем ширину колонок
    worksheet.set_column('A:A', 20)
    worksheet.set_column('B:B', 25)

    workbook.close()
    output.seek(0)

    # Загружаем файл на Яндекс Диск
    await yandex_client.upload_file(upload_url, output.getvalue())
