import threading
from dataclasses import dataclass

from app.domain.common.ids import new_id
from app.domain.common.money import Money
from app.domain.payment.payment import PaymentInstrument
from app.ports.payment_gateway import GatewayResult, PaymentGateway

# Deterministic test instruments, documented in the README.
DECLINED_TOKENS = frozenset(
    {
        "4000000000000002",  # card
        "fail@upi",  # UPI
        "paytm:9000000000",  # wallet
    }
)


@dataclass(frozen=True, slots=True)
class RecordedCall:
    kind: str  # "charge" | "refund"
    reference: str
    amount: Money


class MockPaymentGateway(PaymentGateway):
    """In-process stand-in for a real payment provider.

    Approves everything except ``DECLINED_TOKENS`` and records each call so
    tests can check, for example, that an idempotent replay never charges twice.
    """

    def __init__(self, declined_tokens: frozenset[str] = DECLINED_TOKENS) -> None:
        self._declined = declined_tokens
        self._calls: list[RecordedCall] = []
        self._lock = threading.Lock()

    def charge(self, instrument: PaymentInstrument, amount: Money, order_id: str) -> GatewayResult:
        if instrument.token in self._declined:
            return GatewayResult(success=False, failure_reason="Declined by issuer")
        reference = f"ch_{new_id()}"
        self._record(RecordedCall("charge", reference, amount))
        return GatewayResult(success=True, reference=reference)

    def refund(self, charge_reference: str, amount: Money) -> GatewayResult:
        reference = f"rf_{new_id()}"
        self._record(RecordedCall("refund", charge_reference, amount))
        return GatewayResult(success=True, reference=reference)

    @property
    def calls(self) -> list[RecordedCall]:
        with self._lock:
            return list(self._calls)

    def _record(self, call: RecordedCall) -> None:
        with self._lock:
            self._calls.append(call)
