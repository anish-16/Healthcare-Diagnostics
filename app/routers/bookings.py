from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.enums import BookingStatus
from app.models.models import User
from app.schemas.booking import BookingCreate, BookingOut
from app.services import booking_service

router = APIRouter(prefix="/api/bookings", tags=["Bookings"])


@router.post("", response_model=BookingOut, status_code=status.HTTP_201_CREATED,
             summary="Create a booking (price is taken from the catalogue, never from the client)")
def create_booking(
    payload: BookingCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    return booking_service.create_booking(db, current_user.id, payload)


@router.get("", response_model=list[BookingOut], summary="List the authenticated user's bookings")
def list_bookings(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    status_filter: BookingStatus | None = Query(default=None, alias="status",
                                               description="Filter by booking status"),
):
    return booking_service.list_user_bookings(db, current_user.id, status_filter)


@router.get("/{booking_id}", response_model=BookingOut,
            summary="Get one of the authenticated user's bookings")
def get_booking(
    booking_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    return booking_service.get_own_booking(db, booking_id, current_user.id)


@router.patch("/{booking_id}/cancel", response_model=BookingOut,
              summary="Cancel one of the user's unpaid bookings")
def cancel_booking(
    booking_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    booking = booking_service.get_own_booking(db, booking_id, current_user.id)
    return booking_service.cancel_booking(db, booking)
