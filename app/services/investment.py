from app.core.db import utcnow
from app.models.base import CharityDonationBase


def close_if_fully_invested(obj: CharityDonationBase) -> None:
    if not obj.fully_invested and obj.invested_amount >= obj.full_amount:
        obj.fully_invested = True
        obj.close_date = utcnow()


def invest(
        target: CharityDonationBase,
        sources: list[CharityDonationBase],
) -> list[CharityDonationBase]:
    """Распределить средства между целью и открытыми источниками.

    Возвращает список объектов, которые были изменены: сначала
    задействованные источники, затем сама цель. Вызывающий код добавляет
    их в сессию и сам решает, когда фиксировать транзакцию.
    """
    changed = []
    for source in sources:
        target_needs = target.full_amount - target.invested_amount
        source_available = source.full_amount - source.invested_amount
        investment = min(target_needs, source_available)
        if not investment:
            break
        for obj in (target, source):
            obj.invested_amount += investment
            close_if_fully_invested(obj)
        changed.append(source)
    if changed:
        changed.append(target)
    return changed
