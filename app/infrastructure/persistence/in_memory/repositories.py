from collections.abc import Sequence

from app.domain.booking.booking import Booking
from app.domain.inventory.room_inventory import RoomInventory
from app.domain.property.owner import OwnerAccount
from app.domain.property.property import Property
from app.infrastructure.persistence.in_memory.base import InMemoryStore
from app.ports.repositories import (
    BookingRepository,
    InventoryRepository,
    OwnerRepository,
    PropertyRepository,
)


class InMemoryOwnerRepository(OwnerRepository):
    def __init__(self) -> None:
        self._store: InMemoryStore[str, OwnerAccount] = InMemoryStore()

    def save(self, entity: OwnerAccount) -> None:
        self._store.put(entity.id, entity)

    def find(self, entity_id: str) -> OwnerAccount | None:
        return self._store.get(entity_id)


class InMemoryPropertyRepository(PropertyRepository):
    def __init__(self) -> None:
        self._store: InMemoryStore[str, Property] = InMemoryStore()

    def save(self, entity: Property) -> None:
        self._store.put(entity.id, entity)

    def find(self, entity_id: str) -> Property | None:
        return self._store.get(entity_id)

    def list_by_owner(self, owner_id: str) -> Sequence[Property]:
        return self._store.filter(lambda prop: prop.owner_id == owner_id)

    def find_by_location(self, city: str, locality: str | None = None) -> Sequence[Property]:
        return self._store.filter(lambda prop: prop.location.matches(city, locality))


class InMemoryBookingRepository(BookingRepository):
    def __init__(self) -> None:
        self._store: InMemoryStore[str, Booking] = InMemoryStore()

    def save(self, entity: Booking) -> None:
        self._store.put(entity.id, entity)

    def find(self, entity_id: str) -> Booking | None:
        return self._store.get(entity_id)


class InMemoryInventoryRepository(InventoryRepository):
    def __init__(self) -> None:
        self._store: InMemoryStore[tuple[str, str], RoomInventory] = InMemoryStore()

    def save(self, inventory: RoomInventory) -> None:
        self._store.put((inventory.property_id, inventory.room_type_id), inventory)

    def find(self, property_id: str, room_type_id: str) -> RoomInventory | None:
        return self._store.get((property_id, room_type_id))
