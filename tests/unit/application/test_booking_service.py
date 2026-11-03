from dataclasses import replace
from datetime import date

import pytest

from app.api.container import Container
from app.application.search_service import SearchCriteria
from app.domain.booking.status import BookingStatus
from app.domain.common.exceptions import (
    DomainValidationError,
    InsufficientInventoryError,
    NotFoundError,
)
from app.domain.common.money import Money
from app.domain.property.property import Property
from tests.factories import NOW, booking_request, make_container, onboard_hotel, stay

FEB_1_3 = stay(date(2027, 2, 1), date(2027, 2, 3))


@pytest.fixture
def container() -> Container:
    return make_container()


@pytest.fixture
def hotel(container: Container) -> Property:
    return onboard_hotel(container, units=2, rate=4000)


def _free_units(container: Container, prop: Property, stay_range: object) -> int:
    [room_type_id] = prop.room_types
    return container.inventory.get(prop.id, room_type_id).available_units(stay_range)  # type: ignore[arg-type]


def test_creates_pending_booking_priced_by_strategy(container: Container, hotel: Property) -> None:
    booking = container.booking.create(booking_request(hotel, FEB_1_3, rooms=2, guests=3))

    assert booking.status is BookingStatus.PENDING_PAYMENT
    assert booking.total_price == Money.of(16000)  # 4000 x 2 nights x 2 rooms
    assert booking.created_at == NOW
    assert container.booking.get(booking.id) is booking


def test_booking_holds_inventory(container: Container, hotel: Property) -> None:
    container.booking.create(booking_request(hotel, FEB_1_3))

    assert _free_units(container, hotel, FEB_1_3) == 1


def test_prevents_double_booking_of_overlapping_dates(
    container: Container, hotel: Property
) -> None:
    container.booking.create(booking_request(hotel, FEB_1_3, rooms=2, guests=2))

    overlapping = stay(date(2027, 2, 2), date(2027, 2, 4))
    with pytest.raises(InsufficientInventoryError):
        container.booking.create(booking_request(hotel, overlapping))


def test_back_to_back_stays_are_allowed(container: Container, hotel: Property) -> None:
    container.booking.create(booking_request(hotel, FEB_1_3, rooms=2, guests=2))

    next_stay = stay(date(2027, 2, 3), date(2027, 2, 5))
    assert container.booking.create(booking_request(hotel, next_stay)).id


def test_booked_out_property_disappears_from_search(container: Container, hotel: Property) -> None:
    container.booking.create(booking_request(hotel, FEB_1_3, rooms=2, guests=2))

    criteria = SearchCriteria(city="Bengaluru", stay=FEB_1_3, guests=1)
    assert container.search.search(criteria) == []


def test_failed_validation_does_not_consume_inventory(
    container: Container, hotel: Property
) -> None:
    with pytest.raises(DomainValidationError):
        container.booking.create(booking_request(hotel, FEB_1_3, guests=5, rooms=1))

    assert _free_units(container, hotel, FEB_1_3) == 2


@pytest.mark.parametrize(
    ("overrides", "error"),
    [
        ({"guests": 3, "rooms": 1}, DomainValidationError),  # occupancy is 2
        ({"stay": stay(date(2027, 1, 9), date(2027, 1, 11))}, DomainValidationError),  # past
        ({"guest_name": " "}, DomainValidationError),
        ({"property_id": "ghost"}, NotFoundError),
        ({"room_type_id": "ghost"}, NotFoundError),
    ],
    ids=["over-capacity", "past", "no-name", "unknown-property", "unknown-room-type"],
)
def test_rejects_invalid_requests(
    container: Container, hotel: Property, overrides: dict[str, object], error: type[Exception]
) -> None:
    request = replace(booking_request(hotel, FEB_1_3), **overrides)  # type: ignore[arg-type]

    with pytest.raises(error):
        container.booking.create(request)


def test_get_unknown_booking_raises(container: Container) -> None:
    with pytest.raises(NotFoundError):
        container.booking.get("ghost")
