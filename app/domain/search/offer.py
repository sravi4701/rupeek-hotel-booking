from dataclasses import dataclass

from app.domain.pricing.quote import Quote
from app.domain.property.amenity import Amenity
from app.domain.property.property import Property
from app.domain.property.room_type import RoomType


@dataclass(frozen=True, slots=True)
class RoomOffer:
    """A room type available for the requested stay, priced. This is what search filters see."""

    property: Property
    room_type: RoomType
    quote: Quote
    available_units: int

    def amenities(self) -> frozenset[Amenity]:
        return self.property.all_amenities_for(self.room_type)
