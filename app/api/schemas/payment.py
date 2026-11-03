from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.application.payment_service import PaymentOutcome, PaymentRequest
from app.domain.booking.status import BookingStatus
from app.domain.payment.payment import Payment, PaymentStatus


class PaymentCreate(BaseModel):
    """``details`` depend on ``method``. They're validated by that method's strategy, so a
    new method needs no schema change.

    - card: ``card_number``, ``cvv``
    - upi: ``vpa``
    - wallet: ``provider`` (paytm|phonepe|amazonpay), ``phone``
    """

    method: str = Field(min_length=1, examples=["card"])
    details: dict[str, str] = Field(
        default_factory=dict, examples=[{"card_number": "4242424242424242", "cvv": "123"}]
    )

    def to_request(self, booking_id: str, idempotency_key: str | None) -> PaymentRequest:
        return PaymentRequest(
            booking_id=booking_id,
            method=self.method,
            details=self.details,
            idempotency_key=idempotency_key,
        )


class PaymentOut(BaseModel):
    id: str
    booking_id: str
    method: str
    instrument: str
    amount: Decimal
    currency: str
    status: PaymentStatus
    gateway_reference: str | None
    failure_reason: str | None
    refunded_amount: Decimal | None
    refund_reference: str | None
    created_at: datetime

    @classmethod
    def from_domain(cls, payment: Payment) -> PaymentOut:
        return cls(
            id=payment.id,
            booking_id=payment.booking_id,
            method=payment.method,
            instrument=payment.instrument_display,
            amount=payment.amount.amount,
            currency=payment.amount.currency,
            status=payment.status,
            gateway_reference=payment.gateway_reference,
            failure_reason=payment.failure_reason,
            refunded_amount=payment.refunded_amount.amount if payment.refunded_amount else None,
            refund_reference=payment.refund_reference,
            created_at=payment.created_at,
        )


class PaymentResultOut(BaseModel):
    payment: PaymentOut
    booking_status: BookingStatus

    @classmethod
    def from_outcome(cls, outcome: PaymentOutcome) -> PaymentResultOut:
        return cls(
            payment=PaymentOut.from_domain(outcome.payment),
            booking_status=outcome.booking.status,
        )
