from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from app.domain.common.ids import new_id
from app.domain.common.money import Money


class PaymentStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"


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
    id: str = field(default_factory=new_id)

    @property
    def succeeded(self) -> bool:
        return self.status is PaymentStatus.SUCCEEDED
