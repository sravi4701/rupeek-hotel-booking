from datetime import date, datetime
from decimal import Decimal

import pytest

from app.application.onboarding_service import (
    OnboardingService,
    PropertyDetails,
    RoomTypeDetails,
)
from app.application.search_service import SearchCriteria, SearchService
from app.domain.common.date_range import DateRange
from app.domain.common.exceptions import DomainValidationError
from app.domain.property.amenity import Amenity
from app.domain.property.owner import AccountType
from app.domain.property.property import Property
from app.domain.search.offer import RoomOffer
from app.infrastructure.clock import FixedClock
from app.infrastructure.persistence.in_memory.repositories import (
    InMemoryInventoryRepository,
    InMemoryOwnerRepository,
    InMemoryPropertyRepository,
)
from app.ports.search_filter import SearchFilter
from app.strategies.cancellation.registry import default_cancellation_policies
from app.strategies.filters.amenities import AmenitiesFilter
from app.strategies.filters.price_range import PriceRangeFilter
from app.strategies.pricing.standard import StandardPricing

TODAY = date(2027, 1, 10)
STAY = DateRange(date(2027, 2, 1), date(2027, 2, 3))


class Fixture:
    def __init__(self) -> None:
        self.inventory = InMemoryInventoryRepository()
        properties = InMemoryPropertyRepository()
        self.onboarding = OnboardingService(
            InMemoryOwnerRepository(), properties, self.inventory, default_cancellation_policies()
        )
        self.search = SearchService(
            properties, self.inventory, StandardPricing(), FixedClock(datetime(2027, 1, 10))
        )
        self.owner = self.onboarding.register_owner("Chain", AccountType.CHAIN)

    def add(
        self,
        name: str,
        *,
        city: str = "Bengaluru",
        locality: str = "Koramangala",
        rate: int = 3000,
        units: int = 2,
        occupancy: int = 2,
        amenities: frozenset[Amenity] = frozenset(),
    ) -> Property:
        room = RoomTypeDetails(
            "Standard", max_occupancy=occupancy, total_units=units, nightly_rate=Decimal(rate)
        )
        details = PropertyDetails(
            name=name,
            city=city,
            locality=locality,
            star_rating=3,
            room_types=[room],
            amenities=amenities,
        )
        return self.onboarding.onboard_property(self.owner.id, details)

    def reserve_all(self, prop: Property, stay: DateRange) -> None:
        [room_type] = prop.room_types.values()
        inventory = self.inventory.get(prop.id, room_type.id)
        inventory.reserve(stay, inventory.total_units)

    def names(
        self, criteria: SearchCriteria, filters: list[SearchFilter] | None = None
    ) -> list[str]:
        return [r.property.name for r in self.search.search(criteria, filters or [])]


def _criteria(**overrides: object) -> SearchCriteria:
    kwargs: dict[str, object] = {"city": "Bengaluru", "stay": STAY, "guests": 2}
    kwargs.update(overrides)
    return SearchCriteria(**kwargs)  # type: ignore[arg-type]


@pytest.fixture
def fx() -> Fixture:
    return Fixture()


def test_matches_city_and_optional_locality(fx: Fixture) -> None:
    fx.add("A", locality="Koramangala")
    fx.add("B", locality="Indiranagar")
    fx.add("C", city="Mumbai")

    assert sorted(fx.names(_criteria())) == ["A", "B"]
    assert fx.names(_criteria(locality="indiranagar")) == ["B"]


def test_excludes_room_types_that_cannot_fit_guests(fx: Fixture) -> None:
    fx.add("Small", occupancy=2)

    assert fx.names(_criteria(guests=3)) == []
    assert fx.names(_criteria(guests=3, rooms=2)) == ["Small"]


def test_excludes_properties_sold_out_for_any_night_of_the_stay(fx: Fixture) -> None:
    sold_out = fx.add("SoldOut")
    fx.add("Free")
    fx.reserve_all(sold_out, DateRange(date(2027, 2, 2), date(2027, 2, 3)))  # last night only

    assert fx.names(_criteria()) == ["Free"]


def test_property_is_available_again_for_non_overlapping_dates(fx: Fixture) -> None:
    prop = fx.add("Hotel")
    fx.reserve_all(prop, STAY)

    later = DateRange(STAY.check_out, date(2027, 2, 5))
    assert fx.names(_criteria(stay=later)) == ["Hotel"]


def test_requires_enough_units_for_requested_rooms(fx: Fixture) -> None:
    fx.add("TwoRooms", units=2)

    assert fx.names(_criteria(guests=3, rooms=2)) == ["TwoRooms"]
    assert fx.names(_criteria(guests=3, rooms=3)) == []


def test_applies_every_filter(fx: Fixture) -> None:
    fx.add("Cheap", rate=2000, amenities=frozenset({Amenity.WIFI}))
    fx.add("Pricey", rate=8000, amenities=frozenset({Amenity.WIFI, Amenity.POOL}))

    filters: list[SearchFilter] = [
        AmenitiesFilter([Amenity.WIFI]),
        PriceRangeFilter(max_price=Decimal(5000)),
    ]

    assert fx.names(_criteria(), filters) == ["Cheap"]


def test_results_are_sorted_cheapest_first(fx: Fixture) -> None:
    fx.add("Mid", rate=5000)
    fx.add("Low", rate=2000)
    fx.add("High", rate=9000)

    assert fx.names(_criteria()) == ["Low", "Mid", "High"]


def test_new_filter_plugs_in_without_changing_the_service(fx: Fixture) -> None:
    class NameStartsWith(SearchFilter):
        def __init__(self, prefix: str) -> None:
            self.prefix = prefix

        def matches(self, offer: RoomOffer) -> bool:
            return offer.property.name.startswith(self.prefix)

    fx.add("Sunrise")
    fx.add("Moonlight")

    assert fx.names(_criteria(), [NameStartsWith("Sun")]) == ["Sunrise"]


def test_rejects_check_in_in_the_past(fx: Fixture) -> None:
    past = DateRange(date(2027, 1, 9), date(2027, 1, 11))

    with pytest.raises(DomainValidationError):
        fx.search.search(_criteria(stay=past))


@pytest.mark.parametrize("overrides", [{"guests": 0}, {"rooms": 0}, {"guests": 1, "rooms": 2}])
def test_rejects_invalid_criteria(overrides: dict[str, object]) -> None:
    with pytest.raises(DomainValidationError):
        _criteria(**overrides)
