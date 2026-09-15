"""Тексты сообщений об ошибках и описания ответов API.

Константы используются одновременно валидаторами (в них поднимаются
HTTPException) и описаниями ответов в Swagger-документации, чтобы код и
документация не могли разойтись.
"""

PROJECT_NAME_DUPLICATE = 'Проект с таким именем уже существует!'
PROJECT_NOT_FOUND = 'Проект не найден!'
PROJECT_CLOSED = 'Закрытый проект нельзя редактировать!'
PROJECT_HAS_INVESTMENTS = (
    'В проект были внесены средства, не подлежит удалению!'
)
FULL_AMOUNT_TOO_LOW = (
    'Нельзя установить значение full_amount меньше уже вложенной суммы.'
)

NOT_UNIQUE_NAME_DESCRIPTION = 'Not unique name'
INVALID_OPERATIONS_DESCRIPTION = 'Invalid operations'
PROJECT_NOT_FOUND_DESCRIPTION = 'The project does not exist'
PROJECT_UNDELETABLE_DESCRIPTION = (
    'Нельзя удалять закрытый проект или проект, в который уже были '
    'инвестированы средства.'
)
