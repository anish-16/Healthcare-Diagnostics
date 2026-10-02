from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class TestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str
    created_at: datetime
    updated_at: datetime


class CentreTestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    centre_id: int
    test_id: int
    price: Decimal


class CentreOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    location: str
    created_at: datetime
    updated_at: datetime


class CentreWithTestsOut(CentreOut):
    tests: list[CentreTestOut]
