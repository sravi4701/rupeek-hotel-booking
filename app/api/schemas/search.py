from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Self

from pydantic import BaseModel, Field, model_validator

from app.application.search_service import PropertySearchResult, SearchCriteria
from app.domain.common.date_range import DateRange
from app.domain.property.amenity import Amenity
from app.domain.search.offer import RoomOffer
from app.ports.search_filter import SearchFilter
from app.strategies.filters.amenities import AmenitiesFilter
from app.strategies.filters.price_range import PriceRangeFilter
from app.strategies.filters.star_rating import MinStarRatingFilter


class SearchQuery(BaseModel):
    """Query string for ``GET /properties/search``.

    To add a filter: add a query field here and one line in ``to_filters``.
    """

    city: str = Field(min_length=1, examples=["Bengaluru"])
    locality: str | None = None
    check_in: date
    check_out: date
    guests: int = Field(ge=1)
    rooms: int = Field(default=1, ge=1)
    min_price: Decimal | None = Field(default=None, ge=0, description="Per room per night")
    max_price: Decimal | None = Field(default=None, ge=0, description="Per room per night")
    amenities: list[Amenity] = Field(default_factory=list)
    min_rating: int | None = Field(default=None, ge=1, le=5)

    @model_validator(mode="after")
    def _check_dates(self) -> Self:
        if self.check_out <= self.check_in:
            raise ValueError("check_out must be after check_in")
        return self

    def to_criteria(self) -> SearchCriteria:
        return SearchCriteria(
            city=self.city,
            locality=self.locality,
            stay=DateRange(self.check_in, self.check_out),
            guests=self.guests,
            rooms=self.rooms,
        )

    def to_filters(self) -> list[SearchFilter]:
        filters: list[SearchFilter] = []
        if self.min_price is not None or self.max_price is not None:
            filters.append(PriceRangeFilter(self.min_price, self.max_price))
        if self.amenities:
            filters.append(AmenitiesFilter(self.amenities))
        if self.min_rating is not None:
            filters.append(MinStarRatingFilter(self.min_rating))
        return filters


class RoomOfferOut(BaseModel):
    room_type_id: str
    room_type_name: str
    max_occupancy: int
    available_units: int
    amenities: list[Amenity]
    price_per_room_night: Decimal
    total_price: Decimal
    currency: str

    @classmethod
    def from_domain(cls, offer: RoomOffer) -> RoomOfferOut:
        return cls(
            room_type_id=offer.room_type.id,
            room_type_name=offer.room_type.name,
            max_occupancy=offer.room_type.max_occupancy,
            available_units=offer.available_units,
            amenities=sorted(offer.amenities()),
            price_per_room_night=offer.quote.per_room_night.amount,
            total_price=offer.quote.total.amount,
            currency=offer.quote.total.currency,
        )


class SearchResultOut(BaseModel):
    property_id: str
    name: str
    city: str
    locality: str
    star_rating: int
    offers: list[RoomOfferOut]

    @classmethod
    def from_domain(cls, result: PropertySearchResult) -> SearchResultOut:
        prop = result.property
        return cls(
            property_id=prop.id,
            name=prop.name,
            city=prop.location.city,
            locality=prop.location.locality,
            star_rating=prop.star_rating,
            offers=[RoomOfferOut.from_domain(o) for o in result.offers],
        )
