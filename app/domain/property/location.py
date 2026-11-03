from __future__ import annotations

from dataclasses import dataclass

from app.domain.common.exceptions import DomainValidationError


def _normalise(value: str) -> str:
    return " ".join(value.split()).casefold()


@dataclass(frozen=True, slots=True)
class Location:
    city: str
    locality: str
    address: str = ""

    def __post_init__(self) -> None:
        if not self.city.strip():
            raise DomainValidationError("city is required")
        if not self.locality.strip():
            raise DomainValidationError("locality is required")

    def matches(self, city: str, locality: str | None = None) -> bool:
        """Matches city and optional locality, ignoring case and extra whitespace."""
        if _normalise(self.city) != _normalise(city):
            return False
        return locality is None or _normalise(self.locality) == _normalise(locality)
