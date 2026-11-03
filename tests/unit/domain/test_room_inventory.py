from datetime import date

import pytest

from app.domain.common.date_range import DateRange
from app.domain.common.exceptions import DomainValidationError, InsufficientInventoryError
from app.domain.inventory.room_inventory import RoomInventory


def _stay(start_day: int, end_day: int) -> DateRange:
    return DateRange(date(2027, 3, start_day), date(2027, 3, end_day))


@pytest.fixture
def inventory() -> RoomInventory:
    return RoomInventory(property_id="p1", room_type_id="rt1", total_units=2)


def test_all_units_available_initially(inventory: RoomInventory) -> None:
    assert inventory.available_units(_stay(1, 5)) == 2


def test_reserve_reduces_availability_only_on_booked_nights(inventory: RoomInventory) -> None:
    inventory.reserve(_stay(2, 4), units=1)

    assert inventory.available_units(_stay(1, 2)) == 2
    assert inventory.available_units(_stay(1, 3)) == 1
    assert inventory.available_units(_stay(4, 6)) == 2  # checkout day is free


def test_availability_is_limited_by_busiest_night(inventory: RoomInventory) -> None:
    inventory.reserve(_stay(1, 3), units=1)
    inventory.reserve(_stay(2, 4), units=1)

    assert inventory.available_units(_stay(1, 2)) == 1
    assert inventory.available_units(_stay(1, 5)) == 0


def test_prevents_double_booking_overlapping_dates(inventory: RoomInventory) -> None:
    inventory.reserve(_stay(1, 4), units=2)

    with pytest.raises(InsufficientInventoryError):
        inventory.reserve(_stay(3, 5), units=1)


def test_back_to_back_stays_share_a_unit() -> None:
    single = RoomInventory(property_id="p1", room_type_id="rt1", total_units=1)
    single.reserve(_stay(1, 3), units=1)

    single.reserve(_stay(3, 5), units=1)  # does not raise


def test_rejects_request_larger_than_capacity(inventory: RoomInventory) -> None:
    with pytest.raises(InsufficientInventoryError):
        inventory.reserve(_stay(1, 2), units=3)


def test_release_makes_units_available_again(inventory: RoomInventory) -> None:
    inventory.reserve(_stay(1, 4), units=2)

    inventory.release(_stay(1, 4), units=2)

    assert inventory.available_units(_stay(1, 4)) == 2


def test_cannot_release_more_than_reserved(inventory: RoomInventory) -> None:
    inventory.reserve(_stay(1, 3), units=1)

    with pytest.raises(DomainValidationError):
        inventory.release(_stay(1, 4), units=1)


@pytest.mark.parametrize("units", [0, -1])
def test_units_must_be_positive(inventory: RoomInventory, units: int) -> None:
    with pytest.raises(DomainValidationError):
        inventory.reserve(_stay(1, 2), units=units)
