from typing import Optional

from sqlalchemy import Text, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import CharityDonationBase


class Donation(CharityDonationBase):
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('user.id'))
    comment: Mapped[Optional[str]] = mapped_column(Text)

