from app.domain.common.exceptions import DomainValidationError
from app.domain.property.property import MAX_STARS, MIN_STARS
from app.domain.search.offer import RoomOffer
from app.ports.search_filter import SearchFilter


class MinStarRatingFilter(SearchFilter):
    def __init__(self, min_rating: int) -> None:
        if not MIN_STARS <= min_rating <= MAX_STARS:
            raise DomainValidationError(f"min_rating must be between {MIN_STARS} and {MAX_STARS}")
        self._min_rating = min_rating

    def matches(self, offer: RoomOffer) -> bool:
        return offer.property.star_rating >= self._min_rating
