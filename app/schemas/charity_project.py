from typing import Annotated, Optional

from pydantic import Field

from app.constants import (MAX_NAME_LENGTH, MIN_DESCRIPTION_LENGTH,
                           MIN_NAME_LENGTH)
from app.schemas.base import BaseSchema, CharityDonationDB, FullAmount

Name = Annotated[
    str, Field(min_length=MIN_NAME_LENGTH, max_length=MAX_NAME_LENGTH)
]
Description = Annotated[str, Field(min_length=MIN_DESCRIPTION_LENGTH)]


class CharityProjectCreate(BaseSchema):
    name: Name
    description: Description
    full_amount: FullAmount


class CharityProjectUpdate(BaseSchema):
    name: Optional[Name] = None
    description: Optional[Description] = None
    full_amount: Optional[FullAmount] = None


class CharityProjectDB(CharityProjectCreate, CharityDonationDB):
    pass
