from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass

from app.domain.common.date_range import DateRange
from app.domain.common.exceptions import DomainValidationError
from app.domain.property.property import Property
from app.domain.search.offer import RoomOffer
from app.ports.clock import Clock
from app.ports.pricing import PricingStrategy
from app.ports.repositories import InventoryRepository, PropertyRepository
from app.ports.search_filter import SearchFilter


@dataclass(frozen=True, slots=True)
class SearchCriteria:
    """The mandatory part of a search. Optional criteria are ``SearchFilter``s."""

    city: str
    stay: DateRange
    guests: int
    rooms: int = 1
    locality: str | None = None

    def __post_init__(self) -> None:
        if self.guests < 1:
            raise DomainValidationError("guests must be at least 1")
        if self.rooms < 1:
            raise DomainValidationError("rooms must be at least 1")
        if self.rooms > self.guests:
            raise DomainValidationError("rooms cannot exceed guests")


@dataclass(frozen=True, slots=True)
class PropertySearchResult:
    property: Property
    offers: Sequence[RoomOffer]  # cheapest first


@dataclass(slots=True)
class SearchService:
    """Finds properties with at least one room type that is bookable for the stay.

    For each room type in the location, an offer must:
    1. fit the guests in the requested number of rooms,
    2. have enough free units on every night of the stay,
    3. pass every optional filter (price, amenities, rating, ...).

    Availability is a snapshot read without locks. Booking re-checks it under a lock,
    so a result can sell out before it is booked but can never be double-booked.
    """

    properties: PropertyRepository
    inventory: InventoryRepository
    pricing: PricingStrategy
    clock: Clock

    def search(
        self, criteria: SearchCriteria, filters: Sequence[SearchFilter] = ()
    ) -> list[PropertySearchResult]:
        criteria.stay.require_not_in_past(self.clock.today())

        results = []
        for prop in self.properties.find_by_location(criteria.city, criteria.locality):
            offers = [
                offer
                for offer in self._available_offers(prop, criteria)
                if all(f.matches(offer) for f in filters)
            ]
            if offers:
                offers.sort(key=lambda o: o.quote.total.amount)
                results.append(PropertySearchResult(prop, offers))
        return sorted(results, key=lambda r: r.offers[0].quote.total.amount)

    def _available_offers(self, prop: Property, criteria: SearchCriteria) -> Iterator[RoomOffer]:
        for room_type in prop.room_types.values():
            if not room_type.can_host(criteria.guests, criteria.rooms):
                continue
            free_units = self.inventory.get(prop.id, room_type.id).available_units(criteria.stay)
            if free_units < criteria.rooms:
                continue
            yield RoomOffer(
                property=prop,
                room_type=room_type,
                quote=self.pricing.quote(room_type, criteria.stay, criteria.rooms),
                available_units=free_units,
            )
