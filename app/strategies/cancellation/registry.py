from collections.abc import Iterable
from datetime import timedelta

from app.domain.common.exceptions import DomainValidationError
from app.ports.cancellation import CancellationPolicy
from app.strategies.cancellation.tiered import RefundTier, TieredRefundPolicy

FLEXIBLE = TieredRefundPolicy(
    "flexible",
    "Full refund up to 24h before check-in, 50% after that",
    [RefundTier(timedelta(hours=24), 100), RefundTier(timedelta(0), 50)],
)
MODERATE = TieredRefundPolicy(
    "moderate",
    "Full refund up to 5 days before check-in, 50% up to 24h before, then none",
    [RefundTier(timedelta(days=5), 100), RefundTier(timedelta(hours=24), 50)],
)
NON_REFUNDABLE = TieredRefundPolicy("non_refundable", "No refund", [])


class CancellationPolicyRegistry:
    def __init__(self, policies: Iterable[CancellationPolicy]) -> None:
        self._policies = {policy.name: policy for policy in policies}

    def get(self, name: str) -> CancellationPolicy:
        try:
            return self._policies[name]
        except KeyError:
            raise DomainValidationError(
                f"Unknown cancellation policy '{name}'; supported: {self.names()}"
            ) from None

    def names(self) -> list[str]:
        return sorted(self._policies)


def default_cancellation_policies() -> CancellationPolicyRegistry:
    return CancellationPolicyRegistry([FLEXIBLE, MODERATE, NON_REFUNDABLE])
