from datetime import date

from app.domain.common.date_range import DateRange
from app.domain.common.exceptions import DomainValidationError
from app.domain.common.money import Money
from app.domain.pricing.quote import Quote
from app.domain.property.room_type import RoomType
from app.ports.pricing import PricingStrategy

FRIDAY, SATURDAY = 4, 5


class WeekendSurchargePricing(PricingStrategy):
    """Base rate, plus ``surcharge_percent`` on Friday and Saturday nights."""

    def __init__(self, surcharge_percent: int = 20) -> None:
        if surcharge_percent < 0:
            raise DomainValidationError("surcharge_percent cannot be negative")
        self._surcharge_percent = surcharge_percent

    def quote(self, room_type: RoomType, stay: DateRange, rooms: int) -> Quote:
        per_room = Money.zero(room_type.nightly_rate.currency)
        for night in stay.nights():
            per_room = per_room + self._rate_for(room_type.nightly_rate, night)
        return Quote(total=per_room * rooms, nights=stay.night_count, rooms=rooms)

    def _rate_for(self, base: Money, night: date) -> Money:
        if night.weekday() in (FRIDAY, SATURDAY):
            return base + base.percent(self._surcharge_percent)
        return base
