from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.constants import MAX_NAME_LENGTH
from app.models.base import CharityDonationBase


class CharityProject(CharityDonationBase):
    name: Mapped[str] = mapped_column(String(MAX_NAME_LENGTH), unique=True)
    description: Mapped[str] = mapped_column(Text)
