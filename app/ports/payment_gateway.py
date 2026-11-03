from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.domain.common.money import Money
from app.domain.payment.payment import PaymentInstrument


@dataclass(frozen=True, slots=True)
class GatewayResult:
    success: bool
    reference: str | None = None
    failure_reason: str | None = None


class PaymentGateway(ABC):
    """The external payment provider, seen only through this contract.

    A decline is a normal result, not an exception.
    """

    @abstractmethod
    def charge(
        self, instrument: PaymentInstrument, amount: Money, order_id: str
    ) -> GatewayResult: ...

    @abstractmethod
    def refund(self, charge_reference: str, amount: Money) -> GatewayResult: ...
