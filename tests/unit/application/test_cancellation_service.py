import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta

import pytest

from app.api.container import Container
from app.application.payment_service import PaymentRequest
from app.application.search_service import SearchCriteria
from app.domain.booking.booking import Booking
from app.domain.booking.status import BookingStatus
from app.domain.common.exceptions import (
    DomainValidationError,
    InvalidStateTransitionError,
    RefundFailedError,
)
from app.domain.common.money import Money
from app.domain.payment.payment import PaymentStatus
from app.infrastructure.clock import FixedClock
from app.infrastructure.gateways.mock_payment_gateway import MockPaymentGateway
from app.ports.payment_gateway import GatewayResult
from tests.factories import booking_request, make_container, onboard_hotel, stay

# NOW in the factories is 2027-01-10 12:00. Check-in is Feb 1 at 14:00.
FEB_1_3 = stay(date(2027, 2, 1), date(2027, 2, 3))
CARD = {"card_number": "4242424242424242", "cvv": "123"}


def _book(container: Container, policy: str = "flexible", units: int = 1) -> Booking:
    hotel = onboard_hotel(container, units=units, rate=5000, cancellation_policy=policy)
    return container.booking.create(booking_request(hotel, FEB_1_3))


def _pay(container: Container, booking: Booking) -> None:
    container.payment.pay(PaymentRequest(booking.id, "card", CARD))


def _set_time(container: Container, at: datetime) -> None:
    assert isinstance(container.clock, FixedClock)
    container.clock.advance(at - container.clock.now())


def _free_units(container: Container, booking: Booking) -> int:
    inventory = container.inventory.get(booking.property_id, booking.room_type_id)
    return inventory.available_units(booking.stay)


def _refunds(container: Container) -> list[Money]:
    assert isinstance(container.gateway, MockPaymentGateway)
    return [call.amount for call in container.gateway.calls if call.kind == "refund"]


@pytest.fixture
def container() -> Container:
    return make_container()


class TestUnpaidBooking:
    def test_cancels_without_refund_and_releases_inventory(self, container: Container) -> None:
        booking = _book(container)
        assert _free_units(container, booking) == 0

        cancelled = container.cancellation.cancel(booking.id)

        assert cancelled.status is BookingStatus.CANCELLED
        assert cancelled.refund_amount == Money.zero()
        assert _free_units(container, booking) == 1
        assert _refunds(container) == []


class TestPaidBooking:
    @pytest.mark.parametrize(
        ("policy", "notice", "expected_refund", "payment_status"),
        [
            ("flexible", timedelta(days=3), 10000, PaymentStatus.REFUNDED),
            ("flexible", timedelta(hours=2), 5000, PaymentStatus.PARTIALLY_REFUNDED),
            ("moderate", timedelta(days=2), 5000, PaymentStatus.PARTIALLY_REFUNDED),
        ],
    )
    def test_refunds_through_gateway_per_policy(
        self,
        container: Container,
        policy: str,
        notice: timedelta,
        expected_refund: int,
        payment_status: PaymentStatus,
    ) -> None:
        booking = _book(container, policy)
        _pay(container, booking)
        _set_time(container, booking.check_in_at - notice)

        cancelled = container.cancellation.cancel(booking.id)

        assert cancelled.refund_amount == Money.of(expected_refund)
        assert _refunds(container) == [Money.of(expected_refund)]
        assert cancelled.payment_id is not None
        payment = container.payments.get(cancelled.payment_id)
        assert payment.status is payment_status
        assert payment.refunded_amount == Money.of(expected_refund)

    @pytest.mark.parametrize("policy", ["non_refundable", "moderate"])
    def test_zero_refund_skips_the_gateway(self, container: Container, policy: str) -> None:
        booking = _book(container, policy)
        _pay(container, booking)
        _set_time(container, booking.check_in_at - timedelta(hours=1))

        cancelled = container.cancellation.cancel(booking.id)

        assert cancelled.status is BookingStatus.CANCELLED
        assert cancelled.refund_amount == Money.zero()
        assert _refunds(container) == []

    def test_policy_is_snapshotted_at_booking_time(self, container: Container) -> None:
        booking = _book(container, "flexible")
        _pay(container, booking)
        container.properties.get(booking.property_id).cancellation_policy = "non_refundable"

        assert container.cancellation.cancel(booking.id).refund_amount == Money.of(10000)


class TestInventoryRelease:
    def test_cancelled_rooms_are_searchable_and_bookable_again(self, container: Container) -> None:
        booking = _book(container, units=1)
        criteria = SearchCriteria(city="Bengaluru", stay=FEB_1_3, guests=2)
        assert container.search.search(criteria) == []

        container.cancellation.cancel(booking.id)

        assert len(container.search.search(criteria)) == 1
        prop = container.properties.get(booking.property_id)
        assert container.booking.create(booking_request(prop, FEB_1_3)).id


class TestGuards:
    def test_cannot_cancel_twice(self, container: Container) -> None:
        booking = _book(container)
        container.cancellation.cancel(booking.id)

        with pytest.raises(InvalidStateTransitionError):
            container.cancellation.cancel(booking.id)

    def test_cannot_cancel_after_check_in(self, container: Container) -> None:
        booking = _book(container)
        _set_time(container, booking.check_in_at)

        with pytest.raises(DomainValidationError):
            container.cancellation.cancel(booking.id)
        assert booking.status is BookingStatus.PENDING_PAYMENT
        assert _free_units(container, booking) == 0

    def test_cannot_pay_after_cancellation(self, container: Container) -> None:
        booking = _book(container)
        container.cancellation.cancel(booking.id)

        with pytest.raises(InvalidStateTransitionError):
            _pay(container, booking)


def test_refund_failure_leaves_booking_untouched() -> None:
    class RefusingGateway(MockPaymentGateway):
        def refund(self, charge_reference: str, amount: Money) -> GatewayResult:
            return GatewayResult(success=False, failure_reason="Gateway timeout")

    container = Container(clock=FixedClock(datetime(2027, 1, 10, 12)), gateway=RefusingGateway())
    booking = _book(container)
    _pay(container, booking)

    with pytest.raises(RefundFailedError):
        container.cancellation.cancel(booking.id)

    assert booking.status is BookingStatus.CONFIRMED
    assert _free_units(container, booking) == 0
    assert booking.payment_id is not None
    assert container.payments.get(booking.payment_id).status is PaymentStatus.SUCCEEDED


class SlowRefundGateway(MockPaymentGateway):
    """Refund latency widens the race window. Without the booking lock this test fails."""

    def refund(self, charge_reference: str, amount: Money) -> GatewayResult:
        time.sleep(0.005)
        return super().refund(charge_reference, amount)


def test_concurrent_cancellations_succeed_exactly_once() -> None:
    container = Container(clock=FixedClock(datetime(2027, 1, 10, 12)), gateway=SlowRefundGateway())
    booking = _book(container, units=1)
    _pay(container, booking)
    threads = 20
    barrier = threading.Barrier(threads)

    def attempt(_: int) -> bool:
        barrier.wait()
        try:
            container.cancellation.cancel(booking.id)
        except InvalidStateTransitionError:
            return False
        return True

    with ThreadPoolExecutor(max_workers=threads) as pool:
        results = list(pool.map(attempt, range(threads)))

    assert results.count(True) == 1
    assert len(_refunds(container)) == 1
    assert _free_units(container, booking) == 1  # released once, not 20 times
