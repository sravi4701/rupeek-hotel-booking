from abc import ABC, abstractmethod

from app.domain.search.offer import RoomOffer


class SearchFilter(ABC):
    """One optional search criterion, applied to each available, priced offer.

    To add a filter, implement this interface and build it from the request.
    ``SearchService`` does not change.
    """

    @abstractmethod
    def matches(self, offer: RoomOffer) -> bool: ...
