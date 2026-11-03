from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.domain.booking.status import BookingStatus, can_transition
from app.domain.common.date_range import DateRange
from app.domain.common.exceptions import DomainValidationError, InvalidStateTransitionError
from app.domain.common.ids import new_id
from app.domain.common.money import Money


@dataclass(slots=True)
class Booking:
    """A guest's reservation of ``rooms`` units of one room type for a stay.

    Inventory is held when the booking is created. State changes only go through
    the methods below, so ``ALLOWED_TRANSITIONS`` is always enforced.
    """

    property_id: str
    room_type_id: str
    guest_name: str
    stay: DateRange
    guests: int
    rooms: int
    total_price: Money
    created_at: datetime
    status: BookingStatus = BookingStatus.PENDING_PAYMENT
    payment_id: str | None = None
    failed_payment_attempts: int = 0
    refund_amount: Money | None = None
    cancelled_at: datetime | None = None
    id: str = field(default_factory=new_id)

    def __post_init__(self) -> None:
        if not self.guest_name.strip():
            raise DomainValidationError("guest_name is required")
        if self.guests < 1:
            raise DomainValidationError("guests must be at least 1")
        if self.rooms < 1:
            raise DomainValidationError("rooms must be at least 1")
        if self.rooms > self.guests:
            raise DomainValidationError("Cannot book more rooms than guests")

    def confirm(self, payment_id: str) -> None:
        self._transition_to(BookingStatus.CONFIRMED)
        self.payment_id = payment_id

    def record_failed_payment(self) -> None:
        """A failed attempt leaves the booking pending so the guest can retry."""
        self._require_status(BookingStatus.PENDING_PAYMENT, target="payment attempt")
        self.failed_payment_attempts += 1

    def cancel(self, refund_amount: Money, at: datetime) -> None:
        if refund_amount.amount > 0 and self.status is not BookingStatus.CONFIRMED:
            raise DomainValidationError("Only a paid (confirmed) booking can be refunded")
        if self.total_price < refund_amount:
            raise DomainValidationError("Refund cannot exceed the booking total")
        self._transition_to(BookingStatus.CANCELLED)
        self.refund_amount = refund_amount
        self.cancelled_at = at

    @property
    def is_paid(self) -> bool:
        return self.payment_id is not None

    def _transition_to(self, target: BookingStatus) -> None:
        if not can_transition(self.status, target):
            raise InvalidStateTransitionError("Booking", self.status, target)
        self.status = target

    def _require_status(self, expected: BookingStatus, *, target: str) -> None:
        if self.status is not expected:
            raise InvalidStateTransitionError("Booking", self.status, target)
