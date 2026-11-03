from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from app.domain.common.exceptions import DomainValidationError

_PAISE = Decimal("0.01")
DEFAULT_CURRENCY = "INR"


@dataclass(frozen=True, slots=True)
class Money:
    """Non-negative amount in a single currency, always rounded to 2 decimal places."""

    amount: Decimal
    currency: str = DEFAULT_CURRENCY

    def __post_init__(self) -> None:
        amount = Decimal(self.amount)
        if amount < 0:
            raise DomainValidationError("Money amount cannot be negative")
        object.__setattr__(self, "amount", amount.quantize(_PAISE, rounding=ROUND_HALF_UP))

    @classmethod
    def zero(cls, currency: str = DEFAULT_CURRENCY) -> Money:
        return cls(Decimal(0), currency)

    @classmethod
    def of(cls, amount: str | int | Decimal, currency: str = DEFAULT_CURRENCY) -> Money:
        return cls(Decimal(amount), currency)

    def __add__(self, other: Money) -> Money:
        self._require_same_currency(other)
        return Money(self.amount + other.amount, self.currency)

    def __mul__(self, factor: int | Decimal) -> Money:
        return Money(self.amount * Decimal(factor), self.currency)

    __rmul__ = __mul__

    def __truediv__(self, divisor: int) -> Money:
        if divisor <= 0:
            raise DomainValidationError("Can only divide money by a positive number")
        return Money(self.amount / Decimal(divisor), self.currency)

    def percent(self, pct: int | Decimal) -> Money:
        return Money(self.amount * Decimal(pct) / Decimal(100), self.currency)

    def __lt__(self, other: Money) -> bool:
        self._require_same_currency(other)
        return self.amount < other.amount

    def __le__(self, other: Money) -> bool:
        self._require_same_currency(other)
        return self.amount <= other.amount

    def _require_same_currency(self, other: Money) -> None:
        if self.currency != other.currency:
            raise DomainValidationError(f"Currency mismatch: {self.currency} vs {other.currency}")

    def __str__(self) -> str:
        return f"{self.currency} {self.amount}"
