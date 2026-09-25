import io
from collections.abc import Sequence
from datetime import datetime, timedelta

import xlsxwriter

from app.core.config import settings
from app.core.yandex_client import YandexDiskClient
from app.models.charity_project import CharityProject

HEADERS = ('Название проекта', 'Время сбора', 'Описание')


def format_time_delta(delta: timedelta) -> str:
    """Форматирует timedelta в строку вида 'X дн. Y ч.' или 'Y ч. Z мин.'."""
    days = delta.days
    hours, remainder = divmod(delta.seconds, 3600)
    minutes = remainder // 60
    if days:
        return f'{days} дн. {hours} ч.'
    return f'{hours} ч. {minutes} мин.'


async def create_simple_report(
        yandex_client: YandexDiskClient,
        projects_by_completion_rate: Sequence[CharityProject],
) -> str:
    """Формирует Excel-отчёт, загружает его на Диск и возвращает ссылку."""
    now_date_time = datetime.now().strftime(settings.report_format)
    safe_filename = (
        f'QRKot_report_{now_date_time}'
        .replace(':', '-').replace(' ', '_').replace('/', '-')
    )
    upload_url, file_path = await yandex_client.create_excel_file(
        safe_filename
    )

    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    worksheet = workbook.add_worksheet('Отчёт')

    # Форматы
    title_format = workbook.add_format({
        'bold': True,
        'font_size': 14,
        'border': 1,
        'align': 'center',
    })
    header_format = workbook.add_format({
        'bold': True,
        'bg_color': '#2F75B5',
        'font_color': 'white',
        'border': 1,
        'align': 'center',
    })
    cell_format = workbook.add_format({'border': 1, 'align': 'center'})
    description_format = workbook.add_format({
        'border': 1,
        'text_wrap': True,
        'valign': 'top',
    })
    total_format = workbook.add_format({'bold': True, 'border': 1})

    # Строка 1: заголовок отчёта
    worksheet.merge_range(
        'A1:C1', f'Отчёт от {now_date_time}', title_format
    )

    # Строка 2: заголовки колонок
    for col, header in enumerate(HEADERS):
        worksheet.write(1, col, header, header_format)

    # Строки 3 и далее: данные проектов
    for row, project in enumerate(projects_by_completion_rate, start=2):
        project_duration = format_time_delta(
            project.close_date - project.create_date
        )
        worksheet.write(row, 0, project.name, cell_format)
        worksheet.write(row, 1, project_duration, cell_format)
        worksheet.write(row, 2, project.description, description_format)

    # Последняя строка: итог
    total_row = 2 + len(projects_by_completion_rate)
    worksheet.write(total_row, 0, 'Всего проектов', total_format)
    worksheet.write(
        total_row, 1, len(projects_by_completion_rate), total_format
    )
    worksheet.write_blank(total_row, 2, None, total_format)

    # Ширина колонок
    worksheet.set_column('A:A', 30)
    worksheet.set_column('B:B', 20)
    worksheet.set_column('C:C', 50)

    workbook.close()
    output.seek(0)

    await yandex_client.upload_file(upload_url, output.read())
    return await yandex_client.publish_file(file_path)
