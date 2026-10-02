from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

# All timestamps are UTC: DateTime(timezone=True) columns hold timestamptz values
# and the engine pins the session timezone to UTC (see app.core.database).
TIMESTAMP_KWARGS = {"server_default": func.now()}
TIMESTAMP_UPDATE_KWARGS = {"server_default": func.now(), "onupdate": func.now()}


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), **TIMESTAMP_KWARGS)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), **TIMESTAMP_UPDATE_KWARGS)

    bookings: Mapped[list["Booking"]] = relationship(back_populates="user")


class DiagnosticCentre(Base):
    __tablename__ = "diagnostic_centres"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    location: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), **TIMESTAMP_KWARGS)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), **TIMESTAMP_UPDATE_KWARGS)

    centre_tests: Mapped[list["CentreTest"]] = relationship(back_populates="centre")


class DiagnosticTest(Base):
    __tablename__ = "diagnostic_tests"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), **TIMESTAMP_KWARGS)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), **TIMESTAMP_UPDATE_KWARGS)

    centre_tests: Mapped[list["CentreTest"]] = relationship(back_populates="test")


class CentreTest(Base):
    """A diagnostic test offered at a specific centre, priced per centre."""

    __tablename__ = "centre_tests"

    id: Mapped[int] = mapped_column(primary_key=True)
    centre_id: Mapped[int] = mapped_column(
        ForeignKey("diagnostic_centres.id", ondelete="CASCADE"), index=True
    )
    test_id: Mapped[int] = mapped_column(
        ForeignKey("diagnostic_tests.id", ondelete="CASCADE"), index=True
    )
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), **TIMESTAMP_KWARGS)

    centre: Mapped[DiagnosticCentre] = relationship(back_populates="centre_tests")
    test: Mapped[DiagnosticTest] = relationship(back_populates="centre_tests")
    bookings: Mapped[list["Booking"]] = relationship(back_populates="centre_test")

    __table_args__ = (
        UniqueConstraint("centre_id", "test_id", name="uq_centre_tests_centre_test"),
    )


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    centre_test_id: Mapped[int] = mapped_column(ForeignKey("centre_tests.id"), index=True)
    # Appointment time in UTC; the API accepts any ISO-8601 offset and normalizes to UTC.
    appointment_datetime: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    status: Mapped[str] = mapped_column(String(20), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), **TIMESTAMP_KWARGS)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), **TIMESTAMP_UPDATE_KWARGS)

    user: Mapped[User] = relationship(back_populates="bookings")
    centre_test: Mapped[CentreTest] = relationship(back_populates="bookings")
    payments: Mapped[list["Payment"]] = relationship(back_populates="booking")


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id"), index=True)
    # Provider event id is unique: one row per provider webhook event (idempotency).
    provider_event_id: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    status: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), **TIMESTAMP_KWARGS)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), **TIMESTAMP_UPDATE_KWARGS)

    booking: Mapped[Booking] = relationship(back_populates="payments")
