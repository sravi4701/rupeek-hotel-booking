from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

from app.domain.booking.booking import Booking
from app.domain.common.exceptions import DomainValidationError
from app.domain.common.money import Money
from app.ports.cancellation import CancellationPolicy


@dataclass(frozen=True, slots=True)
class RefundTier:
    """Refund ``percent`` of the total when cancelling at least ``notice`` before check-in."""

    notice: timedelta
    percent: int


class TieredRefundPolicy(CancellationPolicy):
    """Refund percentage set by how much notice the guest gives before check-in.

    The most generous tier the notice qualifies for applies. With no qualifying
    tier, the refund is zero. Most real-world policies (flexible, moderate,
    strict, non-refundable) are just different tier tables, so they need
    configuration, not new code.
    """

    def __init__(self, name: str, description: str, tiers: Sequence[RefundTier]) -> None:
        if any(not 0 <= tier.percent <= 100 for tier in tiers):
            raise DomainValidationError("Refund percent must be between 0 and 100")
        self._name = name
        self._description = description
        self._tiers = sorted(tiers, key=lambda tier: tier.notice, reverse=True)

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    def refund_for(self, booking: Booking, cancelled_at: datetime) -> Money:
        notice = booking.check_in_at - cancelled_at
        for tier in self._tiers:
            if notice >= tier.notice:
                return booking.total_price.percent(tier.percent)
        return Money.zero(booking.total_price.currency)
