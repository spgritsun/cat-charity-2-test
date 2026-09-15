"""Хелперы для описания ответов с ошибками в Swagger-документации.

FastAPI ожидает в параметре `responses` громоздкую вложенную структуру.
Чтобы не повторять её в каждом эндпоинте, здесь собраны функции, которые
строят эту структуру из описания и примеров сообщений.
"""

DETAIL_SCHEMA = {
    'type': 'object',
    'properties': {'detail': {'type': 'string'}},
}


def error_response(description: str, examples: dict = None) -> dict:
    """Собрать описание ответа с ошибкой.

    :param description: текст описания ответа в документации.
    :param examples: словарь вида {ключ: (краткое описание, текст ошибки)}.
    """
    content = {'schema': DETAIL_SCHEMA}
    if examples:
        content['examples'] = {
            key: {'summary': summary, 'value': {'detail': detail}}
            for key, (summary, detail) in examples.items()
        }
    return {
        'description': description,
        'content': {'application/json': content},
    }
