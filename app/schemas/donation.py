from datetime import datetime
from typing import Optional

from app.schemas.base import BaseSchema, CharityDonationDB, FullAmount


class DonationCreate(BaseSchema):
    full_amount: FullAmount
    comment: Optional[str] = None


class DonationDB(DonationCreate):
    id: int
    create_date: datetime


class DonationFullInfoDB(DonationCreate, CharityDonationDB):
    pass
