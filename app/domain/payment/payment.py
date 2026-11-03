from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from app.domain.common.exceptions import DomainValidationError
from app.domain.common.ids import new_id
from app.domain.common.money import Money


class PaymentStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    PARTIALLY_REFUNDED = "partially_refunded"
    REFUNDED = "refunded"


@dataclass(frozen=True, slots=True)
class PaymentInstrument:
    """Method-specific details, checked and normalised by a ``PaymentMethod``.

    ``token`` goes to the gateway. ``display`` is a masked label that is safe to
    store and return to clients, e.g. "card ****4242".
    """

    method: str
    token: str
    display: str


@dataclass(slots=True)
class Payment:
    """One charge attempt against a booking. Failed attempts are kept for the audit trail."""

    booking_id: str
    method: str
    instrument_display: str
    amount: Money
    status: PaymentStatus
    created_at: datetime
    gateway_reference: str | None = None
    failure_reason: str | None = None
    refunded_amount: Money | None = None
    refund_reference: str | None = None
    id: str = field(default_factory=new_id)

    @property
    def declined(self) -> bool:
        return self.status is PaymentStatus.FAILED

    def record_refund(self, amount: Money, reference: str | None) -> None:
        """Supports one refund per payment, matching one cancellation per booking."""
        if self.status is not PaymentStatus.SUCCEEDED:
            raise DomainValidationError(f"Cannot refund a payment that is {self.status}")
        if amount.amount <= 0 or self.amount < amount:
            raise DomainValidationError("Refund must be positive and at most the amount paid")
        self.refunded_amount = amount
        self.refund_reference = reference
        self.status = (
            PaymentStatus.REFUNDED if amount == self.amount else PaymentStatus.PARTIALLY_REFUNDED
        )
