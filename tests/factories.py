"""Shared builders for service-level tests: a fully wired container at a fixed time."""

from datetime import date, datetime
from decimal import Decimal

from app.api.container import Container
from app.application.booking_service import BookingRequest
from app.application.onboarding_service import PropertyDetails, RoomTypeDetails
from app.domain.common.date_range import DateRange
from app.domain.property.owner import AccountType
from app.domain.property.property import Property
from app.infrastructure.clock import FixedClock

NOW = datetime(2027, 1, 10, 12, 0)


def make_container(now: datetime = NOW) -> Container:
    return Container(clock=FixedClock(now))


def onboard_hotel(
    container: Container,
    *,
    units: int = 3,
    occupancy: int = 2,
    rate: int = 4000,
    cancellation_policy: str = "flexible",
) -> Property:
    owner = container.onboarding.register_owner("Owner", AccountType.INDIVIDUAL)
    details = PropertyDetails(
        name="Hotel",
        city="Bengaluru",
        locality="Koramangala",
        star_rating=4,
        cancellation_policy=cancellation_policy,
        room_types=[
            RoomTypeDetails(
                "Deluxe", max_occupancy=occupancy, total_units=units, nightly_rate=Decimal(rate)
            )
        ],
    )
    return container.onboarding.onboard_property(owner.id, details)


def stay(start: date, end: date) -> DateRange:
    return DateRange(start, end)


def booking_request(
    prop: Property,
    stay_range: DateRange,
    *,
    guests: int = 2,
    rooms: int = 1,
    guest_name: str = "Asha",
) -> BookingRequest:
    [room_type_id] = prop.room_types
    return BookingRequest(
        property_id=prop.id,
        room_type_id=room_type_id,
        guest_name=guest_name,
        stay=stay_range,
        guests=guests,
        rooms=rooms,
    )
