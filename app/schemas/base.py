from datetime import datetime
from typing import Annotated, Optional

from pydantic import BaseModel, ConfigDict, Field, PositiveInt

FullAmount = Annotated[PositiveInt, Field(json_schema_extra={'example': 1})]


class BaseSchema(BaseModel):
    model_config = ConfigDict(extra='forbid')


class CharityDonationDB(BaseSchema):
    id: int
    invested_amount: int
    fully_invested: bool
    create_date: datetime
    close_date: Optional[datetime] = None
