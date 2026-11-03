"""Request/response models for owners and properties.

These are the HTTP contract and stay separate from the domain model. Field
constraints here give clients clear 422 errors. The domain still enforces its
own invariants.
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field

from app.application.onboarding_service import PropertyDetails, RoomTypeDetails
from app.domain.property.amenity import Amenity
from app.domain.property.owner import AccountType, OwnerAccount
from app.domain.property.property import Property
from app.domain.property.room_type import RoomType


class OwnerCreate(BaseModel):
    name: str = Field(min_length=1, examples=["Sunrise Hotels"])
    account_type: AccountType = AccountType.INDIVIDUAL


class OwnerOut(BaseModel):
    id: str
    name: str
    account_type: AccountType
    property_ids: list[str]

    @classmethod
    def from_domain(cls, owner: OwnerAccount) -> OwnerOut:
        return cls(
            id=owner.id,
            name=owner.name,
            account_type=owner.account_type,
            property_ids=list(owner.property_ids),
        )


class RoomTypeIn(BaseModel):
    name: str = Field(min_length=1, examples=["Deluxe King"])
    max_occupancy: int = Field(ge=1, examples=[2])
    total_units: int = Field(ge=1, examples=[10])
    nightly_rate: Decimal = Field(gt=0, decimal_places=2, examples=["4500.00"])
    amenities: set[Amenity] = Field(default_factory=set)

    def to_details(self) -> RoomTypeDetails:
        return RoomTypeDetails(
            name=self.name,
            max_occupancy=self.max_occupancy,
            total_units=self.total_units,
            nightly_rate=self.nightly_rate,
            amenities=frozenset(self.amenities),
        )


class PropertyCreate(BaseModel):
    name: str = Field(min_length=1, examples=["Sunrise Koramangala"])
    city: str = Field(min_length=1, examples=["Bengaluru"])
    locality: str = Field(min_length=1, examples=["Koramangala"])
    address: str = ""
    star_rating: int = Field(ge=1, le=5, examples=[4])
    amenities: set[Amenity] = Field(default_factory=set)
    cancellation_policy: str = Field(
        default="flexible", description="One of: flexible, moderate, non_refundable"
    )
    room_types: list[RoomTypeIn] = Field(min_length=1)

    def to_details(self) -> PropertyDetails:
        return PropertyDetails(
            name=self.name,
            city=self.city,
            locality=self.locality,
            address=self.address,
            star_rating=self.star_rating,
            amenities=frozenset(self.amenities),
            cancellation_policy=self.cancellation_policy,
            room_types=[rt.to_details() for rt in self.room_types],
        )


class LocationOut(BaseModel):
    city: str
    locality: str
    address: str


class RoomTypeOut(BaseModel):
    id: str
    name: str
    max_occupancy: int
    total_units: int
    nightly_rate: Decimal
    currency: str
    amenities: list[Amenity]

    @classmethod
    def from_domain(cls, room_type: RoomType) -> RoomTypeOut:
        return cls(
            id=room_type.id,
            name=room_type.name,
            max_occupancy=room_type.max_occupancy,
            total_units=room_type.total_units,
            nightly_rate=room_type.nightly_rate.amount,
            currency=room_type.nightly_rate.currency,
            amenities=sorted(room_type.amenities),
        )


class PropertyOut(BaseModel):
    id: str
    owner_id: str
    name: str
    location: LocationOut
    star_rating: int
    amenities: list[Amenity]
    cancellation_policy: str
    room_types: list[RoomTypeOut]

    @classmethod
    def from_domain(cls, prop: Property) -> PropertyOut:
        return cls(
            id=prop.id,
            owner_id=prop.owner_id,
            name=prop.name,
            location=LocationOut(
                city=prop.location.city,
                locality=prop.location.locality,
                address=prop.location.address,
            ),
            star_rating=prop.star_rating,
            amenities=sorted(prop.amenities),
            cancellation_policy=prop.cancellation_policy,
            room_types=[RoomTypeOut.from_domain(rt) for rt in prop.room_types.values()],
        )
