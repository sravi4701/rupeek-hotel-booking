from collections.abc import Iterable

from app.domain.property.amenity import Amenity
from app.domain.search.offer import RoomOffer
from app.ports.search_filter import SearchFilter


class AmenitiesFilter(SearchFilter):
    """Keeps offers that have every requested amenity, counting property-wide and room amenities."""

    def __init__(self, required: Iterable[Amenity]) -> None:
        self._required = frozenset(required)

    def matches(self, offer: RoomOffer) -> bool:
        return self._required <= offer.amenities()
