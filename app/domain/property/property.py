from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from app.domain.common.exceptions import DomainValidationError, NotFoundError
from app.domain.common.ids import new_id
from app.domain.property.amenity import Amenity
from app.domain.property.location import Location
from app.domain.property.room_type import RoomType

MIN_STARS, MAX_STARS = 1, 5


@dataclass(slots=True)
class Property:
    owner_id: str
    name: str
    location: Location
    star_rating: int
    room_types: dict[str, RoomType]
    amenities: frozenset[Amenity] = frozenset()
    cancellation_policy: str = "flexible"
    id: str = field(default_factory=new_id)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise DomainValidationError("Property name is required")
        if not MIN_STARS <= self.star_rating <= MAX_STARS:
            raise DomainValidationError(f"star_rating must be between {MIN_STARS} and {MAX_STARS}")
        if not self.room_types:
            raise DomainValidationError("A property needs at least one room type")

    @classmethod
    def create(
        cls,
        *,
        owner_id: str,
        name: str,
        location: Location,
        star_rating: int,
        room_types: Iterable[RoomType],
        amenities: Iterable[Amenity] = (),
        cancellation_policy: str = "flexible",
    ) -> Property:
        room_types = list(room_types)
        names = [rt.name.casefold() for rt in room_types]
        if len(names) != len(set(names)):
            raise DomainValidationError("Room type names must be unique within a property")
        return cls(
            owner_id=owner_id,
            name=name,
            location=location,
            star_rating=star_rating,
            room_types={rt.id: rt for rt in room_types},
            amenities=frozenset(amenities),
            cancellation_policy=cancellation_policy,
        )

    def room_type(self, room_type_id: str) -> RoomType:
        try:
            return self.room_types[room_type_id]
        except KeyError:
            raise NotFoundError("RoomType", room_type_id) from None

    def all_amenities_for(self, room_type: RoomType) -> frozenset[Amenity]:
        """Amenities a guest gets in this room: property-wide plus room-specific."""
        return self.amenities | room_type.amenities
