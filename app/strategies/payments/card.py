import re
from collections.abc import Mapping

from app.domain.common.exceptions import DomainValidationError
from app.domain.payment.payment import PaymentInstrument
from app.strategies.payments.base import PaymentMethod

_CARD_NUMBER = re.compile(r"^\d{12,19}$")
_CVV = re.compile(r"^\d{3,4}$")


def passes_luhn(number: str) -> bool:
    total = 0
    for position, char in enumerate(reversed(number)):
        digit = int(char)
        if position % 2 == 1:
            digit = digit * 2 - 9 if digit > 4 else digit * 2
        total += digit
    return total % 10 == 0


class CardPayment(PaymentMethod):
    name = "card"

    def parse(self, details: Mapping[str, str]) -> PaymentInstrument:
        number = self._required(details, "card_number").replace(" ", "")
        cvv = self._required(details, "cvv")
        if not _CARD_NUMBER.match(number) or not passes_luhn(number):
            raise DomainValidationError("Invalid card number")
        if not _CVV.match(cvv):
            raise DomainValidationError("Invalid CVV")
        return PaymentInstrument(method=self.name, token=number, display=f"card ****{number[-4:]}")
