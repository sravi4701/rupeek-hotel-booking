from datetime import date, datetime, timedelta

import pytest

from app.domain.booking.booking import Booking
from app.domain.common.date_range import DateRange
from app.domain.common.exceptions import DomainValidationError
from app.domain.common.money import Money
from app.strategies.cancellation.registry import (
    FLEXIBLE,
    MODERATE,
    NON_REFUNDABLE,
    default_cancellation_policies,
)
from app.strategies.cancellation.tiered import RefundTier, TieredRefundPolicy

BOOKING = Booking(
    property_id="p1",
    room_type_id="rt1",
    guest_name="Asha",
    stay=DateRange(date(2027, 2, 10), date(2027, 2, 12)),
    guests=2,
    rooms=1,
    total_price=Money.of(10000),
    cancellation_policy="flexible",
    created_at=datetime(2027, 1, 1),
)


def _notice(delta: timedelta) -> datetime:
    """Cancellation moment that is ``delta`` before check-in."""
    return BOOKING.check_in_at - delta


@pytest.mark.parametrize(
    ("notice", "expected"),
    [
        (timedelta(days=10), 10000),
        (timedelta(hours=24), 10000),  # boundary is inclusive
        (timedelta(hours=23, minutes=59), 5000),
        (timedelta(minutes=1), 5000),
    ],
)
def test_flexible(notice: timedelta, expected: int) -> None:
    assert FLEXIBLE.refund_for(BOOKING, _notice(notice)) == Money.of(expected)


@pytest.mark.parametrize(
    ("notice", "expected"),
    [
        (timedelta(days=5), 10000),
        (timedelta(days=4, hours=23), 5000),
        (timedelta(hours=24), 5000),
        (timedelta(hours=23), 0),
    ],
)
def test_moderate(notice: timedelta, expected: int) -> None:
    assert MODERATE.refund_for(BOOKING, _notice(notice)) == Money.of(expected)


def test_non_refundable_never_refunds() -> None:
    assert NON_REFUNDABLE.refund_for(BOOKING, _notice(timedelta(days=60))) == Money.zero()


def test_custom_tier_table_is_just_configuration() -> None:
    strict = TieredRefundPolicy("strict", "75% up to 14 days", [RefundTier(timedelta(days=14), 75)])

    assert strict.refund_for(BOOKING, _notice(timedelta(days=20))) == Money.of(7500)
    assert strict.refund_for(BOOKING, _notice(timedelta(days=13))) == Money.zero()


def test_rejects_invalid_percent() -> None:
    with pytest.raises(DomainValidationError):
        TieredRefundPolicy("bad", "", [RefundTier(timedelta(0), 150)])


def test_registry() -> None:
    registry = default_cancellation_policies()

    assert registry.names() == ["flexible", "moderate", "non_refundable"]
    assert registry.get("moderate") is MODERATE
    with pytest.raises(DomainValidationError, match="Unknown cancellation policy"):
        registry.get("lenient")
