from abc import ABC, abstractmethod

from app.domain.common.date_range import DateRange
from app.domain.pricing.quote import Quote
from app.domain.property.room_type import RoomType


class PricingStrategy(ABC):
    """Prices a stay. Search and booking share it, so the quoted price is the charged price."""

    @abstractmethod
    def quote(self, room_type: RoomType, stay: DateRange, rooms: int) -> Quote: ...
