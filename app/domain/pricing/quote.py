from dataclasses import dataclass

from app.domain.common.money import Money


@dataclass(frozen=True, slots=True)
class Quote:
    """Price for a whole stay: ``rooms`` units for ``nights`` nights."""

    total: Money
    nights: int
    rooms: int

    @property
    def per_room_night(self) -> Money:
        """Average price per room per night. Price filters use this."""
        return self.total / (self.nights * self.rooms)
