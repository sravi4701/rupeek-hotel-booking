import re
from collections.abc import Mapping

from app.domain.common.exceptions import DomainValidationError
from app.domain.payment.payment import PaymentInstrument
from app.strategies.payments.base import PaymentMethod

_PHONE = re.compile(r"^[6-9]\d{9}$")
SUPPORTED_PROVIDERS = frozenset({"paytm", "phonepe", "amazonpay"})


class WalletPayment(PaymentMethod):
    name = "wallet"

    def parse(self, details: Mapping[str, str]) -> PaymentInstrument:
        provider = self._required(details, "provider").lower()
        phone = self._required(details, "phone")
        if provider not in SUPPORTED_PROVIDERS:
            raise DomainValidationError(
                f"Unsupported wallet provider; choose one of {sorted(SUPPORTED_PROVIDERS)}"
            )
        if not _PHONE.match(phone):
            raise DomainValidationError("Invalid phone number")
        return PaymentInstrument(
            method=self.name, token=f"{provider}:{phone}", display=f"{provider} ******{phone[-4:]}"
        )
