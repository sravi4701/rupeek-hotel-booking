import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date

import pytest

from app.api.container import Container
from app.application.payment_service import PaymentOutcome, PaymentRequest
from app.domain.booking.booking import Booking
from app.domain.booking.status import BookingStatus
from app.domain.common.exceptions import (
    DomainValidationError,
    IdempotencyConflictError,
    InvalidStateTransitionError,
)
from app.domain.common.money import Money
from app.domain.payment.payment import PaymentInstrument, PaymentStatus
from app.infrastructure.clock import FixedClock
from app.infrastructure.gateways.mock_payment_gateway import MockPaymentGateway
from app.ports.payment_gateway import GatewayResult
from tests.factories import NOW, booking_request, make_container, onboard_hotel, stay

GOOD_CARD = {"card_number": "4242424242424242", "cvv": "123"}
DECLINED_CARD = {"card_number": "4000000000000002", "cvv": "123"}


class SlowGateway(MockPaymentGateway):
    """Network latency on charge widens the race window for the concurrency tests."""

    def charge(self, instrument: PaymentInstrument, amount: Money, order_id: str) -> GatewayResult:
        time.sleep(0.005)
        return super().charge(instrument, amount, order_id)


@pytest.fixture
def container() -> Container:
    return make_container()


@pytest.fixture
def slow_container() -> Container:
    return Container(clock=FixedClock(NOW), gateway=SlowGateway())


@pytest.fixture
def slow_booking(slow_container: Container) -> Booking:
    hotel = onboard_hotel(slow_container, units=2, rate=4000)
    return slow_container.booking.create(
        booking_request(hotel, stay(date(2027, 2, 1), date(2027, 2, 3)))
    )


@pytest.fixture
def booking(container: Container) -> Booking:
    hotel = onboard_hotel(container, units=2, rate=4000)
    return container.booking.create(
        booking_request(hotel, stay(date(2027, 2, 1), date(2027, 2, 3)))
    )


def _gateway(container: Container) -> MockPaymentGateway:
    assert isinstance(container.gateway, MockPaymentGateway)
    return container.gateway


def _pay(
    container: Container,
    booking: Booking,
    details: dict[str, str] = GOOD_CARD,
    method: str = "card",
    key: str | None = None,
) -> PaymentOutcome:
    return container.payment.pay(PaymentRequest(booking.id, method, details, key))


class TestOutcomeDrivesBookingState:
    def test_success_confirms_booking(self, container: Container, booking: Booking) -> None:
        outcome = _pay(container, booking)

        assert outcome.payment.status is PaymentStatus.SUCCEEDED
        assert outcome.payment.amount == Money.of(8000)
        assert outcome.payment.instrument_display == "card ****4242"
        assert outcome.payment.created_at == NOW
        assert outcome.booking.status is BookingStatus.CONFIRMED
        assert outcome.booking.payment_id == outcome.payment.id
        assert [c.kind for c in _gateway(container).calls] == ["charge"]

    def test_decline_keeps_booking_pending(self, container: Container, booking: Booking) -> None:
        outcome = _pay(container, booking, DECLINED_CARD)

        assert outcome.payment.status is PaymentStatus.FAILED
        assert outcome.payment.failure_reason == "Declined by issuer"
        assert outcome.booking.status is BookingStatus.PENDING_PAYMENT
        assert outcome.booking.failed_payment_attempts == 1

    def test_retry_after_decline_with_another_method(
        self, container: Container, booking: Booking
    ) -> None:
        _pay(container, booking, DECLINED_CARD)

        outcome = _pay(container, booking, {"vpa": "asha@okhdfc"}, method="upi")

        assert outcome.booking.status is BookingStatus.CONFIRMED
        attempts = container.payment.list_payments(booking.id)
        assert [p.status for p in attempts] == [PaymentStatus.FAILED, PaymentStatus.SUCCEEDED]


class TestGuards:
    def test_cannot_pay_confirmed_booking_twice(
        self, container: Container, booking: Booking
    ) -> None:
        _pay(container, booking)

        with pytest.raises(InvalidStateTransitionError):
            _pay(container, booking)
        assert len(_gateway(container).calls) == 1

    def test_cannot_pay_cancelled_booking(self, container: Container, booking: Booking) -> None:
        booking.cancel(Money.zero(), at=NOW)

        with pytest.raises(InvalidStateTransitionError):
            _pay(container, booking)
        assert _gateway(container).calls == []

    def test_invalid_details_never_reach_gateway(
        self, container: Container, booking: Booking
    ) -> None:
        with pytest.raises(DomainValidationError):
            _pay(container, booking, {"card_number": "123", "cvv": "1"})

        assert _gateway(container).calls == []
        assert booking.status is BookingStatus.PENDING_PAYMENT
        assert container.payment.list_payments(booking.id) == []


class TestIdempotency:
    def test_replay_returns_original_payment_without_recharging(
        self, container: Container, booking: Booking
    ) -> None:
        first = _pay(container, booking, key="key-1")

        second = _pay(container, booking, key="key-1")

        assert second.replayed
        assert second.payment.id == first.payment.id
        assert second.booking.status is BookingStatus.CONFIRMED
        assert len(_gateway(container).calls) == 1

    def test_replay_of_declined_attempt_returns_the_decline(
        self, container: Container, booking: Booking
    ) -> None:
        first = _pay(container, booking, DECLINED_CARD, key="key-1")

        second = _pay(container, booking, DECLINED_CARD, key="key-1")

        assert second.payment.id == first.payment.id
        assert booking.failed_payment_attempts == 1

    def test_reusing_key_with_different_body_conflicts(
        self, container: Container, booking: Booking
    ) -> None:
        _pay(container, booking, DECLINED_CARD, key="key-1")

        with pytest.raises(IdempotencyConflictError):
            _pay(container, booking, GOOD_CARD, key="key-1")

    def test_concurrent_requests_with_same_key_charge_once(
        self, slow_container: Container, slow_booking: Booking
    ) -> None:
        container, booking = slow_container, slow_booking
        threads = 20
        barrier = threading.Barrier(threads)

        def attempt(_: int) -> str:
            barrier.wait()
            return _pay(container, booking, key="same-key").payment.id

        with ThreadPoolExecutor(max_workers=threads) as pool:
            payment_ids = set(pool.map(attempt, range(threads)))

        assert len(payment_ids) == 1
        assert len(_gateway(container).calls) == 1


def test_concurrent_payments_with_different_keys_confirm_exactly_once(
    slow_container: Container, slow_booking: Booking
) -> None:
    container, booking = slow_container, slow_booking
    threads = 20
    barrier = threading.Barrier(threads)

    def attempt(index: int) -> bool:
        barrier.wait()
        try:
            _pay(container, booking, key=f"key-{index}")
        except InvalidStateTransitionError:
            return False
        return True

    with ThreadPoolExecutor(max_workers=threads) as pool:
        results = list(pool.map(attempt, range(threads)))

    assert results.count(True) == 1
    assert len(_gateway(container).calls) == 1
