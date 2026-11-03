from app.domain.common.date_range import DateRange
from app.domain.pricing.quote import Quote
from app.domain.property.room_type import RoomType
from app.ports.pricing import PricingStrategy


class StandardPricing(PricingStrategy):
    """Base nightly rate x nights x rooms."""

    def quote(self, room_type: RoomType, stay: DateRange, rooms: int) -> Quote:
        total = room_type.nightly_rate * (stay.night_count * rooms)
        return Quote(total=total, nights=stay.night_count, rooms=rooms)
