from __future__ import annotations

from dataclasses import dataclass

from app.application.inventory_allocator import InventoryAllocator
from app.domain.booking.booking import Booking
from app.domain.common.date_range import DateRange
from app.domain.common.exceptions import DomainValidationError
from app.ports.clock import Clock
from app.ports.pricing import PricingStrategy
from app.ports.repositories import BookingRepository, PropertyRepository


@dataclass(frozen=True, slots=True)
class BookingRequest:
    property_id: str
    room_type_id: str
    guest_name: str
    stay: DateRange
    guests: int
    rooms: int = 1


@dataclass(slots=True)
class BookingService:
    """Creates bookings. Each new booking holds inventory until it is cancelled.

    Order of steps:
    1. Validate everything that doesn't touch shared state (property, room type,
       dates, capacity, the Booking invariants).
    2. Reserve inventory atomically. On a lost race this raises
       InsufficientInventoryError and nothing has been written.
    3. Persist the booking as PENDING_PAYMENT.
    """

    properties: PropertyRepository
    bookings: BookingRepository
    allocator: InventoryAllocator
    pricing: PricingStrategy
    clock: Clock

    def create(self, request: BookingRequest) -> Booking:
        booking = self._build_booking(request)

        self.allocator.reserve(
            booking.property_id, booking.room_type_id, booking.stay, booking.rooms
        )
        self.bookings.save(booking)
        return booking

    def get(self, booking_id: str) -> Booking:
        return self.bookings.get(booking_id)

    def _build_booking(self, request: BookingRequest) -> Booking:
        room_type = self.properties.get(request.property_id).room_type(request.room_type_id)
        request.stay.require_not_in_past(self.clock.today())
        if not room_type.can_host(request.guests, request.rooms):
            raise DomainValidationError(
                f"{request.rooms} x {room_type.name} cannot host {request.guests} guests"
            )
        quote = self.pricing.quote(room_type, request.stay, request.rooms)
        return Booking(
            property_id=request.property_id,
            room_type_id=request.room_type_id,
            guest_name=request.guest_name,
            stay=request.stay,
            guests=request.guests,
            rooms=request.rooms,
            total_price=quote.total,
            created_at=self.clock.now(),
        )
