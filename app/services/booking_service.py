import uuid
from datetime import timezone

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.models.enums import BOOKING_TRANSITIONS, BookingStatus, PaymentStatus
from app.models.models import Booking, CentreTest, Payment


def _raise_if_invalid_transition(current, target: BookingStatus) -> None:
    current_status = BookingStatus(current)  # accepts enum or the raw string from the DB
    if target not in BOOKING_TRANSITIONS[current_status]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot change booking from {current_status.value} to {target.value}",
        )


def create_booking(db: Session, user_id: int, payload) -> Booking:
    """Create a PENDING booking, resolving the amount from the centre_tests row.

    The client never supplies an amount — the current catalogue price is authoritative.
    """
    centre_test = db.get(CentreTest, payload.centre_test_id)
    if centre_test is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Centre/test not found")

    booking = Booking(
        user_id=user_id,
        centre_test_id=centre_test.id,
        appointment_datetime=payload.appointment_datetime.astimezone(timezone.utc),
        amount=centre_test.price,
        status=BookingStatus.PENDING,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


def get_own_booking(db: Session, booking_id: int, user_id: int) -> Booking:
    booking = (
        db.query(Booking)
        .options(joinedload(Booking.centre_test).joinedload(CentreTest.test))
        .filter(Booking.id == booking_id)
        .first()
    )
    if booking is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    if booking.user_id != user_id:
        # A real resource of another user: hide it rather than reveal its existence.
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Not allowed to access this booking")
    return booking


def list_user_bookings(db: Session, user_id: int, status_filter: BookingStatus | None = None):
    query = (
        db.query(Booking)
        .options(joinedload(Booking.centre_test).joinedload(CentreTest.test))
        .filter(Booking.user_id == user_id)
    )
    if status_filter is not None:
        query = query.filter(Booking.status == status_filter)
    return query.order_by(Booking.created_at.desc()).all()


def cancel_booking(db: Session, booking: Booking) -> Booking:
    _raise_if_invalid_transition(booking.status, BookingStatus.CANCELLED)
    booking.status = BookingStatus.CANCELLED
    db.commit()
    db.refresh(booking)
    return booking


def initiate_payment(db: Session, user_id: int, payload) -> Payment:
    """Simulate a payment attempt for the caller's own booking.

    The amount always comes from the stored booking; the outcome is controlled
    by `payload.simulate` (default success) so both paths are reproducible.
    """
    booking = get_own_booking(db, payload.booking_id, user_id)  # 404 / 403 checks

    # Lock the row so two concurrent payment attempts cannot both go through.
    booking = db.query(Booking).filter(Booking.id == booking.id).with_for_update().one()

    if booking.status != BookingStatus.PENDING:
        detail = {
            BookingStatus.CONFIRMED: "Booking is already paid and confirmed",
            BookingStatus.FAILED: "Booking payment previously failed; create a new booking",
            BookingStatus.CANCELLED: "Booking is cancelled",
        }[BookingStatus(booking.status)]
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)

    will_succeed = payload.simulate != "failure"
    payment = Payment(
        booking_id=booking.id,
        provider_event_id=f"evt_sim_{uuid.uuid4().hex[:12]}",
        amount=booking.amount,
        status=PaymentStatus.SUCCESS if will_succeed else PaymentStatus.FAILED,
    )
    # One transaction: the payment row and the booking status move together.
    db.add(payment)
    booking.status = BookingStatus.CONFIRMED if will_succeed else BookingStatus.FAILED
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="Payment event already recorded")
    db.refresh(payment)
    return payment


def process_webhook(db: Session, event) -> tuple[Payment, bool]:
    """Apply a provider payment event at-most-once (idempotent by event_id).

    Returns the payment and whether this delivery was a duplicate of one
    already processed. The unique constraint on payments.provider_event_id is
    the real guarantee: a replayed event either commits as the first delivery
    or loses the insert race and is acknowledged as a duplicate. Invalid state
    transitions are rejected before anything is written.
    """
    # Row lock serializes near-simultaneous events for the same booking.
    booking = db.query(Booking).filter(Booking.id == event.booking_id).with_for_update().first()
    if booking is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")

    payment = db.query(Payment).filter(Payment.provider_event_id == event.event_id).first()
    if payment is not None:
        if payment.booking_id != booking.id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail="event_id already used for a different booking")
        return payment, True  # duplicate delivery: no state change

    outcome = PaymentStatus(event.status)
    target = BookingStatus.CONFIRMED if outcome is PaymentStatus.SUCCESS else BookingStatus.FAILED
    _raise_if_invalid_transition(booking.status, target)  # reject before writing anything

    payment = Payment(
        booking_id=booking.id,
        provider_event_id=event.event_id,
        amount=booking.amount,
        status=outcome,
    )
    db.add(payment)
    try:
        booking.status = target
        db.commit()
    except IntegrityError:
        db.rollback()
        # Lost the insert race against an identical concurrent delivery.
        payment = db.query(Payment).filter(Payment.provider_event_id == event.event_id).first()
        if payment is None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Payment event conflict")
        if payment.booking_id != booking.id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail="event_id already used for a different booking")
    return payment, False
