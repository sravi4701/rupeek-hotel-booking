from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import ClassVar

from app.domain.common.exceptions import DomainValidationError
from app.domain.payment.payment import PaymentInstrument


class PaymentMethod(ABC):
    """One way to pay (card, UPI, wallet, ...).

    Each method checks its own raw details and turns them into a
    ``PaymentInstrument``. Adding a method is a new subclass plus a registry
    entry. Neither the payment service nor the API changes.
    """

    name: ClassVar[str]

    @abstractmethod
    def parse(self, details: Mapping[str, str]) -> PaymentInstrument: ...

    @staticmethod
    def _required(details: Mapping[str, str], key: str) -> str:
        value = details.get(key, "").strip()
        if not value:
            raise DomainValidationError(f"'{key}' is required")
        return value
