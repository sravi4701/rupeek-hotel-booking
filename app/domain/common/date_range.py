from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date, timedelta

from app.domain.common.exceptions import DomainValidationError

MAX_STAY_NIGHTS = 30


@dataclass(frozen=True, slots=True)
class DateRange:
    """A stay as the half-open interval [check_in, check_out).

    The check-out day is not a night of the stay, so one guest can check out on the
    same day another guest checks in to the same room.
    """

    check_in: date
    check_out: date

    def __post_init__(self) -> None:
        if self.check_out <= self.check_in:
            raise DomainValidationError("check_out must be after check_in")
        if self.night_count > MAX_STAY_NIGHTS:
            raise DomainValidationError(f"Stay cannot exceed {MAX_STAY_NIGHTS} nights")

    @property
    def night_count(self) -> int:
        return (self.check_out - self.check_in).days

    def nights(self) -> Iterator[date]:
        for offset in range(self.night_count):
            yield self.check_in + timedelta(days=offset)

    def overlaps(self, other: DateRange) -> bool:
        return self.check_in < other.check_out and other.check_in < self.check_out

    def starts_before(self, day: date) -> bool:
        return self.check_in < day
