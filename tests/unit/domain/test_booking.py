from datetime import date, datetime

import pytest

from app.domain.booking.booking import Booking
from app.domain.booking.status import ALLOWED_TRANSITIONS, BookingStatus
from app.domain.common.date_range import DateRange
from app.domain.common.exceptions import DomainValidationError, InvalidStateTransitionError
from app.domain.common.money import Money

NOW = datetime(2027, 1, 1, 10, 0)


def _booking(**overrides: object) -> Booking:
    kwargs: dict[str, object] = {
        "property_id": "p1",
        "room_type_id": "rt1",
        "guest_name": "Asha",
        "stay": DateRange(date(2027, 2, 1), date(2027, 2, 3)),
        "guests": 2,
        "rooms": 1,
        "total_price": Money.of(6000),
        "created_at": NOW,
    }
    kwargs.update(overrides)
    return Booking(**kwargs)  # type: ignore[arg-type]


def _confirmed() -> Booking:
    booking = _booking()
    booking.confirm(payment_id="pay-1")
    return booking


def _cancelled() -> Booking:
    booking = _booking()
    booking.cancel(Money.zero(), at=NOW)
    return booking


class TestCreation:
    def test_starts_pending_payment(self) -> None:
        booking = _booking()

        assert booking.status is BookingStatus.PENDING_PAYMENT
        assert not booking.is_paid

    @pytest.mark.parametrize(
        "overrides",
        [{"guests": 0}, {"rooms": 0}, {"rooms": 3, "guests": 2}, {"guest_name": " "}],
    )
    def test_rejects_invalid_input(self, overrides: dict[str, object]) -> None:
        with pytest.raises(DomainValidationError):
            _booking(**overrides)


class TestLifecycle:
    def test_payment_success_confirms(self) -> None:
        booking = _confirmed()

        assert booking.status is BookingStatus.CONFIRMED
        assert booking.payment_id == "pay-1"

    def test_failed_payment_keeps_booking_pending_for_retry(self) -> None:
        booking = _booking()

        booking.record_failed_payment()
        booking.record_failed_payment()

        assert booking.status is BookingStatus.PENDING_PAYMENT
        assert booking.failed_payment_attempts == 2

    def test_cancel_unpaid_booking_without_refund(self) -> None:
        booking = _cancelled()

        assert booking.status is BookingStatus.CANCELLED
        assert booking.refund_amount == Money.zero()
        assert booking.cancelled_at == NOW

    def test_cancel_confirmed_booking_with_refund(self) -> None:
        booking = _confirmed()

        booking.cancel(Money.of(3000), at=NOW)

        assert booking.status is BookingStatus.CANCELLED
        assert booking.refund_amount == Money.of(3000)

    def test_unpaid_booking_cannot_be_refunded(self) -> None:
        with pytest.raises(DomainValidationError):
            _booking().cancel(Money.of(1), at=NOW)

    def test_refund_cannot_exceed_total(self) -> None:
        with pytest.raises(DomainValidationError):
            _confirmed().cancel(Money.of(6001), at=NOW)


class TestInvalidTransitions:
    def test_cannot_confirm_twice(self) -> None:
        with pytest.raises(InvalidStateTransitionError):
            _confirmed().confirm(payment_id="pay-2")

    def test_cannot_confirm_cancelled(self) -> None:
        with pytest.raises(InvalidStateTransitionError):
            _cancelled().confirm(payment_id="pay-1")

    def test_cannot_cancel_twice(self) -> None:
        with pytest.raises(InvalidStateTransitionError):
            _cancelled().cancel(Money.zero(), at=NOW)

    @pytest.mark.parametrize("factory", [_confirmed, _cancelled], ids=["confirmed", "cancelled"])
    def test_cannot_record_payment_attempt_unless_pending(self, factory: object) -> None:
        with pytest.raises(InvalidStateTransitionError):
            factory().record_failed_payment()  # type: ignore[operator]

    def test_cancelled_is_terminal(self) -> None:
        assert ALLOWED_TRANSITIONS[BookingStatus.CANCELLED] == frozenset()
