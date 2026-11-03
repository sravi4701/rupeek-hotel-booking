from datetime import date

import pytest

from app.domain.common.date_range import MAX_STAY_NIGHTS, DateRange
from app.domain.common.exceptions import DomainValidationError
from app.domain.common.money import Money
from app.domain.property.location import Location


class TestMoney:
    def test_rounds_to_two_decimals(self) -> None:
        assert Money.of("10.005").amount == Money.of("10.01").amount

    def test_rejects_negative_amount(self) -> None:
        with pytest.raises(DomainValidationError):
            Money.of(-1)

    def test_arithmetic(self) -> None:
        assert Money.of(100) + Money.of(50) == Money.of(150)
        assert Money.of(100) * 3 == Money.of(300)
        assert Money.of(200).percent(50) == Money.of(100)

    def test_rejects_currency_mismatch(self) -> None:
        with pytest.raises(DomainValidationError):
            _ = Money.of(1, "INR") + Money.of(1, "USD")


class TestDateRange:
    def test_counts_nights_excluding_checkout_day(self) -> None:
        stay = DateRange(date(2027, 1, 1), date(2027, 1, 4))

        assert stay.night_count == 3
        assert list(stay.nights()) == [date(2027, 1, 1), date(2027, 1, 2), date(2027, 1, 3)]

    @pytest.mark.parametrize(
        "check_out", [date(2027, 1, 1), date(2026, 12, 31)], ids=["same-day", "before"]
    )
    def test_checkout_must_be_after_checkin(self, check_out: date) -> None:
        with pytest.raises(DomainValidationError):
            DateRange(date(2027, 1, 1), check_out)

    def test_rejects_overly_long_stay(self) -> None:
        start = date(2027, 1, 1)
        with pytest.raises(DomainValidationError):
            DateRange(start, date.fromordinal(start.toordinal() + MAX_STAY_NIGHTS + 1))

    def test_overlap_is_half_open(self) -> None:
        first = DateRange(date(2027, 1, 1), date(2027, 1, 3))

        assert first.overlaps(DateRange(date(2027, 1, 2), date(2027, 1, 5)))
        assert not first.overlaps(DateRange(date(2027, 1, 3), date(2027, 1, 5)))


class TestLocation:
    def test_matches_case_and_whitespace_insensitively(self) -> None:
        location = Location(city="Bengaluru", locality="Koramangala")

        assert location.matches("  bengaluru ")
        assert location.matches("BENGALURU", "koramangala")
        assert not location.matches("Bengaluru", "Indiranagar")
        assert not location.matches("Mumbai")

    def test_requires_city_and_locality(self) -> None:
        with pytest.raises(DomainValidationError):
            Location(city=" ", locality="Koramangala")
