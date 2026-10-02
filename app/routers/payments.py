from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.models import Booking, Payment, User
from app.schemas.payment import PaymentInitiate, PaymentOut, WebhookAck, WebhookEvent
from app.services import booking_service

router = APIRouter(prefix="/api/payments", tags=["Payments"])


@router.post("", response_model=PaymentOut, status_code=status.HTTP_201_CREATED,
             summary="Initiate a simulated payment for the user's own booking",
             description=(
                 "The amount is always taken from the stored booking, never from the client. "
                 "Pass simulate=failure to reproduce the failed-payment path; the default "
                 "outcome is success. No real payment gateway is used."
             ))
def initiate_payment(
    payload: PaymentInitiate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return booking_service.initiate_payment(db, current_user.id, payload)


@router.get("", response_model=list[PaymentOut],
            summary="List the authenticated user's payments")
def list_payments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(Payment)
        .join(Booking, Payment.booking_id == Booking.id)
        .filter(Booking.user_id == current_user.id)
        .order_by(Payment.created_at.desc())
        .all()
    )


@router.get("/{payment_id}", response_model=PaymentOut,
            summary="Get one of the authenticated user's payments")
def get_payment(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    payment = (
        db.query(Payment)
        .join(Booking, Payment.booking_id == Booking.id)
        .filter(Payment.id == payment_id, Booking.user_id == current_user.id)
        .first()
    )
    if payment is None:
        # Missing, or owned by someone else — both return 404.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    return payment


@router.post("/webhook", response_model=WebhookAck, summary="Payment provider webhook",
             description=(
                 "Receives simulated provider payment events. Idempotent by event_id: "
                 "replaying the same event returns received=true, duplicate=true and leaves "
                 "state unchanged. In a real system this endpoint would verify the "
                 "provider's signature before trusting the payload."
             ))
def payment_webhook(event: WebhookEvent, db: Annotated[Session, Depends(get_db)]):
    payment, duplicate = booking_service.process_webhook(db, event)
    return WebhookAck(
        received=True,
        duplicate=duplicate,
        payment_status=payment.status,
        booking_status=payment.booking.status,
    )
