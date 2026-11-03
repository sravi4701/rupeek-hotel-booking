"""Persistence contracts.

Application services depend only on these interfaces. Swapping the in-memory
adapters for a real database means writing new implementations, nothing else.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from app.domain.booking.booking import Booking
from app.domain.common.exceptions import NotFoundError
from app.domain.inventory.room_inventory import RoomInventory
from app.domain.property.owner import OwnerAccount
from app.domain.property.property import Property


class Repository[T](ABC):
    """Common shape: ``find`` returns None for a missing id, ``get`` raises NotFoundError."""

    entity_name: str = "Entity"

    @abstractmethod
    def save(self, entity: T) -> None: ...

    @abstractmethod
    def find(self, entity_id: str) -> T | None: ...

    def get(self, entity_id: str) -> T:
        entity = self.find(entity_id)
        if entity is None:
            raise NotFoundError(self.entity_name, entity_id)
        return entity


class OwnerRepository(Repository[OwnerAccount], ABC):
    entity_name = "Owner"


class PropertyRepository(Repository[Property], ABC):
    entity_name = "Property"

    @abstractmethod
    def list_by_owner(self, owner_id: str) -> Sequence[Property]: ...

    @abstractmethod
    def find_by_location(self, city: str, locality: str | None = None) -> Sequence[Property]: ...


class BookingRepository(Repository[Booking], ABC):
    entity_name = "Booking"


class InventoryRepository(ABC):
    """Inventory has a composite key (property_id, room_type_id) instead of its own id."""

    @abstractmethod
    def save(self, inventory: RoomInventory) -> None: ...

    @abstractmethod
    def find(self, property_id: str, room_type_id: str) -> RoomInventory | None: ...

    def get(self, property_id: str, room_type_id: str) -> RoomInventory:
        inventory = self.find(property_id, room_type_id)
        if inventory is None:
            raise NotFoundError("Inventory", f"{property_id}/{room_type_id}")
        return inventory
