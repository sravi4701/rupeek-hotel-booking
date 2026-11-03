from __future__ import annotations

from dataclasses import dataclass, field

from app.domain.common.exceptions import DomainValidationError
from app.domain.common.ids import new_id
from app.domain.common.money import Money
from app.domain.property.amenity import Amenity


@dataclass(frozen=True, slots=True)
class RoomType:
    """A category of identical rooms in a property, e.g. 10 x "Deluxe King"."""

    name: str
    max_occupancy: int
    total_units: int
    nightly_rate: Money
    amenities: frozenset[Amenity] = frozenset()
    id: str = field(default_factory=new_id)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise DomainValidationError("Room type name is required")
        if self.max_occupancy < 1:
            raise DomainValidationError("max_occupancy must be at least 1")
        if self.total_units < 1:
            raise DomainValidationError("total_units must be at least 1")
        if self.nightly_rate.amount <= 0:
            raise DomainValidationError("nightly_rate must be positive")

    def can_host(self, guests: int, rooms: int) -> bool:
        return guests <= self.max_occupancy * rooms
