from typing import Optional

from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import CharityDonationBase


class Donation(CharityDonationBase):
    comment: Mapped[Optional[str]] = mapped_column(Text)
