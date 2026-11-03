from datetime import datetime

import pytest

from app.domain.common.exceptions import DomainValidationError
from app.domain.common.money import Money
from app.domain.payment.payment import Payment, PaymentStatus


def _payment(status: PaymentStatus = PaymentStatus.SUCCEEDED) -> Payment:
    return Payment(
        booking_id="b1",
        method="card",
        instrument_display="card ****4242",
        amount=Money.of(8000),
        status=status,
        created_at=datetime(2027, 1, 1),
        gateway_reference="ch_1",
    )


def test_full_refund() -> None:
    payment = _payment()

    payment.record_refund(Money.of(8000), "rf_1")

    assert payment.status is PaymentStatus.REFUNDED
    assert payment.refunded_amount == Money.of(8000)
    assert payment.refund_reference == "rf_1"


def test_partial_refund() -> None:
    payment = _payment()

    payment.record_refund(Money.of(4000), "rf_1")

    assert payment.status is PaymentStatus.PARTIALLY_REFUNDED


@pytest.mark.parametrize("amount", [0, 8001])
def test_refund_must_be_positive_and_within_amount(amount: int) -> None:
    with pytest.raises(DomainValidationError):
        _payment().record_refund(Money.of(amount), "rf_1")


def test_only_one_refund_per_payment() -> None:
    payment = _payment()
    payment.record_refund(Money.of(1000), "rf_1")

    with pytest.raises(DomainValidationError):
        payment.record_refund(Money.of(1000), "rf_2")


def test_failed_payment_cannot_be_refunded() -> None:
    with pytest.raises(DomainValidationError):
        _payment(PaymentStatus.FAILED).record_refund(Money.of(1), "rf_1")
