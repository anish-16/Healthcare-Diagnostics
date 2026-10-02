from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import PaymentStatus


class PaymentInitiate(BaseModel):
    booking_id: int = Field(gt=0, examples=[1])
    # Simulation control only: forces the outcome of this payment attempt.
    simulate: str | None = Field(
        default=None,
        pattern="^(success|failure)$",
        examples=["failure"],
        description="Optional simulation control: 'success' or 'failure'. "
        "Omit for default (success).",
    )


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    booking_id: int
    provider_event_id: str
    amount: Decimal
    status: PaymentStatus
    created_at: datetime
    updated_at: datetime


class WebhookEvent(BaseModel):
    """Payload sent by the (simulated) payment provider."""

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "event_id": "evt_2f8c9a6d1b",
            "booking_id": 1,
            "status": "SUCCESS",
        }
    })

    event_id: str = Field(min_length=6, max_length=120, examples=["evt_2f8c9a6d1b"])
    booking_id: int = Field(gt=0, examples=[1])
    status: PaymentStatus


class WebhookAck(BaseModel):
    received: bool
    duplicate: bool
    payment_status: PaymentStatus | None = None
    booking_status: str | None = None
