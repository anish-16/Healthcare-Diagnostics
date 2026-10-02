from enum import Enum


class BookingStatus(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class PaymentStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


# Allowed booking status transitions. Bookings start PENDING; payment results
# move them to CONFIRMED or FAILED; unpaid and failed bookings can be cancelled.
# CONFIRMED is final here — cancelling a paid booking would need a refund flow,
# which is out of scope for this assignment.
BOOKING_TRANSITIONS: dict[BookingStatus, set[BookingStatus]] = {
    BookingStatus.PENDING: {BookingStatus.CONFIRMED, BookingStatus.FAILED, BookingStatus.CANCELLED},
    BookingStatus.CONFIRMED: set(),
    BookingStatus.FAILED: {BookingStatus.CANCELLED},
    BookingStatus.CANCELLED: set(),
}
