import re
from collections.abc import Mapping

from app.domain.common.exceptions import DomainValidationError
from app.domain.payment.payment import PaymentInstrument
from app.strategies.payments.base import PaymentMethod

_VPA = re.compile(r"^[a-zA-Z0-9.\-_]{2,256}@[a-zA-Z]{2,64}$")


class UpiPayment(PaymentMethod):
    name = "upi"

    def parse(self, details: Mapping[str, str]) -> PaymentInstrument:
        vpa = self._required(details, "vpa").lower()
        if not _VPA.match(vpa):
            raise DomainValidationError("Invalid UPI id (expected name@bank)")
        return PaymentInstrument(method=self.name, token=vpa, display=f"upi {vpa}")
