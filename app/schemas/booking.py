from datetime import datetime, timezone
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import BookingStatus


class BookingCreate(BaseModel):
    centre_test_id: int = Field(gt=0, examples=[3])
    # ISO-8601 with a UTC offset (e.g. "2026-10-05T10:30:00+05:30"); stored and
    # returned in UTC. Timestamps without an offset are rejected.
    appointment_datetime: datetime = Field(examples=["2026-10-05T10:30:00+05:30"])

    @field_validator("appointment_datetime")
    @classmethod
    def validate_appointment(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("appointment_datetime must include a UTC offset")
        if value <= datetime.now(timezone.utc):
            raise ValueError("appointment_datetime must be in the future")
        return value


class BookingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    centre_test_id: int
    appointment_datetime: datetime
    # Serialized as string to keep exact decimal money values in JSON.
    amount: Decimal
    status: BookingStatus
    created_at: datetime
    updated_at: datetime
