from datetime import date
from decimal import Decimal

import pytest

from app.domain.common.date_range import DateRange
from app.domain.common.exceptions import DomainValidationError
from app.domain.common.money import Money
from app.domain.property.amenity import Amenity
from app.domain.property.location import Location
from app.domain.property.property import Property
from app.domain.property.room_type import RoomType
from app.domain.search.offer import RoomOffer
from app.strategies.filters.amenities import AmenitiesFilter
from app.strategies.filters.price_range import PriceRangeFilter
from app.strategies.filters.star_rating import MinStarRatingFilter
from app.strategies.pricing.standard import StandardPricing

STAY = DateRange(date(2027, 5, 1), date(2027, 5, 3))  # 2 nights


def _offer(
    rate: int = 3000,
    stars: int = 3,
    property_amenities: frozenset[Amenity] = frozenset(),
    room_amenities: frozenset[Amenity] = frozenset(),
    rooms: int = 1,
) -> RoomOffer:
    room = RoomType(
        name="Deluxe",
        max_occupancy=2,
        total_units=5,
        nightly_rate=Money.of(rate),
        amenities=room_amenities,
    )
    prop = Property.create(
        owner_id="o1",
        name="Test",
        location=Location("Pune", "Baner"),
        star_rating=stars,
        room_types=[room],
        amenities=property_amenities,
    )
    return RoomOffer(prop, room, StandardPricing().quote(room, STAY, rooms), available_units=5)


class TestStandardPricing:
    def test_total_is_rate_times_nights_times_rooms(self) -> None:
        offer = _offer(rate=3000, rooms=2)

        assert offer.quote.total == Money.of(12000)
        assert offer.quote.per_room_night == Money.of(3000)


class TestPriceRangeFilter:
    @pytest.mark.parametrize(
        ("low", "high", "expected"),
        [
            (None, None, True),
            (Decimal(3000), Decimal(3000), True),  # bounds are inclusive
            (Decimal(3001), None, False),
            (None, Decimal(2999), False),
            (Decimal(1000), Decimal(5000), True),
        ],
    )
    def test_uses_price_per_room_night(
        self, low: Decimal | None, high: Decimal | None, expected: bool
    ) -> None:
        # 2 rooms x 2 nights: total 12000, but per room-night it is 3000
        assert PriceRangeFilter(low, high).matches(_offer(rate=3000, rooms=2)) is expected

    def test_rejects_inverted_range(self) -> None:
        with pytest.raises(DomainValidationError):
            PriceRangeFilter(Decimal(5000), Decimal(1000))


class TestAmenitiesFilter:
    def test_counts_property_and_room_amenities(self) -> None:
        offer = _offer(
            property_amenities=frozenset({Amenity.WIFI}),
            room_amenities=frozenset({Amenity.AIR_CONDITIONING}),
        )

        assert AmenitiesFilter([Amenity.WIFI, Amenity.AIR_CONDITIONING]).matches(offer)
        assert not AmenitiesFilter([Amenity.WIFI, Amenity.POOL]).matches(offer)

    def test_empty_requirement_matches_everything(self) -> None:
        assert AmenitiesFilter([]).matches(_offer())


class TestMinStarRatingFilter:
    def test_keeps_properties_at_or_above_rating(self) -> None:
        assert MinStarRatingFilter(4).matches(_offer(stars=4))
        assert MinStarRatingFilter(4).matches(_offer(stars=5))
        assert not MinStarRatingFilter(4).matches(_offer(stars=3))

    @pytest.mark.parametrize("rating", [0, 6])
    def test_rejects_out_of_range_rating(self, rating: int) -> None:
        with pytest.raises(DomainValidationError):
            MinStarRatingFilter(rating)
