from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.application.inventory_allocator import InventoryAllocator
from app.application.lock_keys import booking_lock
from app.domain.booking.booking import Booking
from app.domain.common.exceptions import RefundFailedError
from app.domain.common.money import Money
from app.ports.clock import Clock
from app.ports.locks import LockProvider
from app.ports.payment_gateway import PaymentGateway
from app.ports.repositories import BookingRepository, PaymentRepository
from app.strategies.cancellation.registry import CancellationPolicyRegistry


@dataclass(slots=True)
class CancellationService:
    """Cancels a booking, refunds it under its policy, and frees its rooms.

    Order of steps, all under the booking's lock (so a cancellation can't race
    a payment or a second cancellation):
    1. Guard: the booking can still be cancelled. Nothing has changed yet.
    2. Work out the refund. Unpaid bookings get nothing, paid ones get what the
       policy gives.
    3. Refund through the gateway. If that fails, stop with the booking unchanged.
    4. Mark the booking CANCELLED and release its inventory so it's bookable again.
    """

    bookings: BookingRepository
    payments: PaymentRepository
    policies: CancellationPolicyRegistry
    gateway: PaymentGateway
    allocator: InventoryAllocator
    locks: LockProvider
    clock: Clock

    def cancel(self, booking_id: str) -> Booking:
        with self.locks.hold(booking_lock(booking_id)):
            booking = self.bookings.get(booking_id)
            now = self.clock.now()
            booking.require_cancellable(now)

            refund = self._refund_amount(booking, now)
            if refund.amount > 0:
                self._refund(booking, refund)

            booking.cancel(refund, at=now)
            self.bookings.save(booking)
            self.allocator.release(
                booking.property_id, booking.room_type_id, booking.stay, booking.rooms
            )
            return booking

    def _refund_amount(self, booking: Booking, now: datetime) -> Money:
        if not booking.is_paid:
            return Money.zero(booking.total_price.currency)
        return self.policies.get(booking.cancellation_policy).refund_for(booking, now)

    def _refund(self, booking: Booking, amount: Money) -> None:
        assert booking.payment_id is not None
        payment = self.payments.get(booking.payment_id)
        assert payment.gateway_reference is not None
        result = self.gateway.refund(payment.gateway_reference, amount)
        if not result.success:
            raise RefundFailedError(result.failure_reason or "Refund was rejected by the gateway")
        payment.record_refund(amount, result.reference)
        self.payments.save(payment)
