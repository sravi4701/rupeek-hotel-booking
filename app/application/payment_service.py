from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from contextlib import ExitStack
from dataclasses import dataclass

from app.application.lock_keys import booking_lock, idempotency_lock
from app.domain.booking.booking import Booking
from app.domain.common.exceptions import IdempotencyConflictError
from app.domain.payment.payment import Payment, PaymentStatus
from app.ports.clock import Clock
from app.ports.locks import LockProvider
from app.ports.payment_gateway import PaymentGateway
from app.ports.repositories import (
    BookingRepository,
    IdempotencyRecord,
    IdempotencyStore,
    PaymentRepository,
)
from app.strategies.payments.registry import PaymentMethodRegistry


@dataclass(frozen=True, slots=True)
class PaymentRequest:
    booking_id: str
    method: str
    details: Mapping[str, str]
    idempotency_key: str | None = None

    def fingerprint(self) -> str:
        """Hash of the request body. A key reused with a different body is a client bug."""
        canonical = json.dumps(
            {"booking": self.booking_id, "method": self.method.lower(), "details": self.details},
            sort_keys=True,
        )
        return hashlib.sha256(canonical.encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class PaymentOutcome:
    payment: Payment
    booking: Booking
    replayed: bool = False


@dataclass(slots=True)
class PaymentService:
    """Charges a booking, and the payment result decides the booking's next state.

    - success: booking -> CONFIRMED
    - decline: booking stays PENDING_PAYMENT with the attempt recorded; the guest may retry
    - booking not PENDING_PAYMENT: InvalidStateTransitionError, and the gateway is never called

    All of this runs under the booking's lock, so a payment can't race a
    cancellation or another payment for the same booking. A repeated
    idempotency key returns the stored result and does not charge again.
    """

    bookings: BookingRepository
    payments: PaymentRepository
    idempotency: IdempotencyStore
    methods: PaymentMethodRegistry
    gateway: PaymentGateway
    locks: LockProvider
    clock: Clock

    def pay(self, request: PaymentRequest) -> PaymentOutcome:
        with ExitStack() as stack:
            if request.idempotency_key:
                stack.enter_context(self.locks.hold(idempotency_lock(request.idempotency_key)))
                replay = self._replay(request)
                if replay:
                    return replay
            stack.enter_context(self.locks.hold(booking_lock(request.booking_id)))

            outcome = self._charge(request)
            if request.idempotency_key:
                self.idempotency.save(
                    request.idempotency_key,
                    IdempotencyRecord(request.fingerprint(), outcome.payment.id),
                )
            return outcome

    def list_payments(self, booking_id: str) -> Sequence[Payment]:
        self.bookings.get(booking_id)
        return self.payments.list_by_booking(booking_id)

    def _replay(self, request: PaymentRequest) -> PaymentOutcome | None:
        assert request.idempotency_key
        record = self.idempotency.find(request.idempotency_key)
        if record is None:
            return None
        if record.request_fingerprint != request.fingerprint():
            raise IdempotencyConflictError(
                "Idempotency-Key was already used with a different request"
            )
        return PaymentOutcome(
            payment=self.payments.get(record.payment_id),
            booking=self.bookings.get(request.booking_id),
            replayed=True,
        )

    def _charge(self, request: PaymentRequest) -> PaymentOutcome:
        booking = self.bookings.get(request.booking_id)
        booking.require_awaiting_payment()
        instrument = self.methods.get(request.method).parse(request.details)

        result = self.gateway.charge(instrument, booking.total_price, order_id=booking.id)

        payment = Payment(
            booking_id=booking.id,
            method=instrument.method,
            instrument_display=instrument.display,
            amount=booking.total_price,
            status=PaymentStatus.SUCCEEDED if result.success else PaymentStatus.FAILED,
            gateway_reference=result.reference,
            failure_reason=result.failure_reason,
            created_at=self.clock.now(),
        )
        self.payments.save(payment)
        if payment.declined:
            booking.record_failed_payment()
        else:
            booking.confirm(payment.id)
        self.bookings.save(booking)
        return PaymentOutcome(payment=payment, booking=booking)
