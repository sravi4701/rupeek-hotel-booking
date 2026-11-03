from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date

from app.domain.common.date_range import DateRange
from app.domain.common.exceptions import DomainValidationError, InsufficientInventoryError


@dataclass(slots=True)
class RoomInventory:
    """Counts booked units per night for one room type.

    The domain object is not thread-safe. The application layer makes each
    check-and-reserve atomic by holding a lock keyed by (property, room type).
    """

    property_id: str
    room_type_id: str
    total_units: int
    _booked: defaultdict[date, int] = field(
        default_factory=lambda: defaultdict(int), init=False, repr=False
    )

    def available_units(self, stay: DateRange) -> int:
        busiest_night = max(self._booked.get(night, 0) for night in stay.nights())
        return self.total_units - busiest_night

    def can_accommodate(self, stay: DateRange, units: int) -> bool:
        return self.available_units(stay) >= units

    def reserve(self, stay: DateRange, units: int) -> None:
        self._require_positive(units)
        if not self.can_accommodate(stay, units):
            raise InsufficientInventoryError(
                f"Only {self.available_units(stay)} unit(s) left for the requested dates"
            )
        for night in stay.nights():
            self._booked[night] += units

    def release(self, stay: DateRange, units: int) -> None:
        self._require_positive(units)
        if any(self._booked.get(night, 0) < units for night in stay.nights()):
            raise DomainValidationError("Cannot release more units than were reserved")
        for night in stay.nights():
            self._booked[night] -= units
            if self._booked[night] == 0:
                del self._booked[night]

    @staticmethod
    def _require_positive(units: int) -> None:
        if units < 1:
            raise DomainValidationError("units must be at least 1")
