from datetime import date

import pytest

from app.domain.common.date_range import DateRange
from app.domain.common.exceptions import DomainValidationError
from app.domain.common.money import Money
from app.domain.property.room_type import RoomType
from app.strategies.pricing.registry import pricing_strategy
from app.strategies.pricing.standard import StandardPricing
from app.strategies.pricing.weekend_surcharge import WeekendSurchargePricing

ROOM = RoomType(name="Deluxe", max_occupancy=2, total_units=5, nightly_rate=Money.of(1000))


def _stay(start: date, end: date) -> DateRange:
    return DateRange(start, end)


class TestWeekendSurcharge:
    def test_weekday_nights_cost_base_rate(self) -> None:
        mon_to_thu = _stay(date(2027, 3, 1), date(2027, 3, 4))  # Mon, Tue, Wed nights

        assert WeekendSurchargePricing(20).quote(ROOM, mon_to_thu, rooms=1).total == Money.of(3000)

    def test_friday_and_saturday_nights_are_surcharged(self) -> None:
        thu_to_sun = _stay(date(2027, 3, 4), date(2027, 3, 7))  # Thu, Fri, Sat nights

        quote = WeekendSurchargePricing(20).quote(ROOM, thu_to_sun, rooms=2)

        assert quote.total == Money.of((1000 + 1200 + 1200) * 2)
        assert quote.per_room_night == Money.of("1133.33")

    def test_sunday_night_is_not_a_weekend_night(self) -> None:
        sunday = _stay(date(2027, 3, 7), date(2027, 3, 8))

        assert WeekendSurchargePricing(20).quote(ROOM, sunday, rooms=1).total == Money.of(1000)

    def test_zero_surcharge_matches_standard_pricing(self) -> None:
        week = _stay(date(2027, 3, 1), date(2027, 3, 8))

        assert (
            WeekendSurchargePricing(0).quote(ROOM, week, 3).total
            == StandardPricing().quote(ROOM, week, 3).total
        )

    def test_rejects_negative_surcharge(self) -> None:
        with pytest.raises(DomainValidationError):
            WeekendSurchargePricing(-5)


class TestRegistry:
    def test_resolves_known_strategies(self) -> None:
        assert isinstance(pricing_strategy("standard"), StandardPricing)
        assert isinstance(pricing_strategy("weekend"), WeekendSurchargePricing)

    def test_unknown_strategy_fails_fast(self) -> None:
        with pytest.raises(ValueError, match="Unknown pricing strategy"):
            pricing_strategy("surge")
