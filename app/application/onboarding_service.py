from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from app.domain.common.money import Money
from app.domain.inventory.room_inventory import RoomInventory
from app.domain.property.amenity import Amenity
from app.domain.property.location import Location
from app.domain.property.owner import AccountType, OwnerAccount
from app.domain.property.property import Property
from app.domain.property.room_type import RoomType
from app.ports.repositories import InventoryRepository, OwnerRepository, PropertyRepository


@dataclass(frozen=True, slots=True)
class RoomTypeDetails:
    name: str
    max_occupancy: int
    total_units: int
    nightly_rate: Decimal
    amenities: frozenset[Amenity] = frozenset()


@dataclass(frozen=True, slots=True)
class PropertyDetails:
    name: str
    city: str
    locality: str
    star_rating: int
    room_types: Sequence[RoomTypeDetails]
    address: str = ""
    amenities: frozenset[Amenity] = frozenset()
    cancellation_policy: str = "flexible"


@dataclass(slots=True)
class OnboardingService:
    """Registers owners and onboards their properties.

    Standalone hotels and chains use the same path. A standalone hotel is an
    owner that has onboarded exactly one property.
    """

    owners: OwnerRepository
    properties: PropertyRepository
    inventory: InventoryRepository

    def register_owner(self, name: str, account_type: AccountType) -> OwnerAccount:
        owner = OwnerAccount(name=name, account_type=account_type)
        self.owners.save(owner)
        return owner

    def get_owner(self, owner_id: str) -> OwnerAccount:
        return self.owners.get(owner_id)

    def onboard_property(self, owner_id: str, details: PropertyDetails) -> Property:
        owner = self.owners.get(owner_id)
        prop = self._build_property(owner_id, details)

        self.properties.save(prop)
        for room_type in prop.room_types.values():
            self.inventory.save(
                RoomInventory(
                    property_id=prop.id,
                    room_type_id=room_type.id,
                    total_units=room_type.total_units,
                )
            )
        owner.add_property(prop.id)
        self.owners.save(owner)
        return prop

    def list_properties(self, owner_id: str) -> Sequence[Property]:
        self.owners.get(owner_id)  # 404 for an unknown owner, not an empty list
        return self.properties.list_by_owner(owner_id)

    def get_property(self, property_id: str) -> Property:
        return self.properties.get(property_id)

    @staticmethod
    def _build_property(owner_id: str, details: PropertyDetails) -> Property:
        return Property.create(
            owner_id=owner_id,
            name=details.name,
            location=Location(details.city, details.locality, details.address),
            star_rating=details.star_rating,
            amenities=details.amenities,
            cancellation_policy=details.cancellation_policy,
            room_types=[
                RoomType(
                    name=rt.name,
                    max_occupancy=rt.max_occupancy,
                    total_units=rt.total_units,
                    nightly_rate=Money(rt.nightly_rate),
                    amenities=rt.amenities,
                )
                for rt in details.room_types
            ],
        )
