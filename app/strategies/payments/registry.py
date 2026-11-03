from collections.abc import Iterable

from app.domain.common.exceptions import DomainValidationError
from app.strategies.payments.base import PaymentMethod
from app.strategies.payments.card import CardPayment
from app.strategies.payments.upi import UpiPayment
from app.strategies.payments.wallet import WalletPayment


class PaymentMethodRegistry:
    def __init__(self, methods: Iterable[PaymentMethod]) -> None:
        self._methods = {method.name: method for method in methods}

    def get(self, name: str) -> PaymentMethod:
        try:
            return self._methods[name.lower()]
        except KeyError:
            raise DomainValidationError(
                f"Unsupported payment method '{name}'; supported: {self.names()}"
            ) from None

    def names(self) -> list[str]:
        return sorted(self._methods)


def default_payment_methods() -> PaymentMethodRegistry:
    return PaymentMethodRegistry([CardPayment(), UpiPayment(), WalletPayment()])
