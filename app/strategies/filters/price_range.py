from decimal import Decimal

from app.domain.common.exceptions import DomainValidationError
from app.domain.search.offer import RoomOffer
from app.ports.search_filter import SearchFilter


class PriceRangeFilter(SearchFilter):
    """Keeps offers whose average price per room-night is within [min_price, max_price]."""

    def __init__(self, min_price: Decimal | None = None, max_price: Decimal | None = None) -> None:
        if min_price is not None and max_price is not None and min_price > max_price:
            raise DomainValidationError("min_price cannot be greater than max_price")
        self._min = min_price
        self._max = max_price

    def matches(self, offer: RoomOffer) -> bool:
        price = offer.quote.per_room_night.amount
        if self._min is not None and price < self._min:
            return False
        return self._max is None or price <= self._max
