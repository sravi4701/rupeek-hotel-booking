from fastapi import APIRouter, status

from app.api.dependencies import BookingServiceDep
from app.api.schemas.booking import BookingCreate, BookingOut

router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    responses={409: {"description": "Not enough rooms left for the requested dates"}},
)
def create_booking(body: BookingCreate, service: BookingServiceDep) -> BookingOut:
    """Hold inventory and create a booking in PENDING_PAYMENT."""
    return BookingOut.from_domain(service.create(body.to_request()))


@router.get("/{booking_id}")
def get_booking(booking_id: str, service: BookingServiceDep) -> BookingOut:
    return BookingOut.from_domain(service.get(booking_id))
