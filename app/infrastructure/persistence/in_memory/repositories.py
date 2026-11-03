from collections.abc import Sequence

from app.domain.booking.booking import Booking
from app.domain.inventory.room_inventory import RoomInventory
from app.domain.payment.payment import Payment
from app.domain.property.owner import OwnerAccount
from app.domain.property.property import Property
from app.infrastructure.persistence.in_memory.base import InMemoryStore
from app.ports.repositories import (
    BookingRepository,
    IdempotencyRecord,
    IdempotencyStore,
    InventoryRepository,
    OwnerRepository,
    PaymentRepository,
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


class InMemoryPaymentRepository(PaymentRepository):
    def __init__(self) -> None:
        self._store: InMemoryStore[str, Payment] = InMemoryStore()

    def save(self, entity: Payment) -> None:
        self._store.put(entity.id, entity)

    def find(self, entity_id: str) -> Payment | None:
        return self._store.get(entity_id)

    def list_by_booking(self, booking_id: str) -> Sequence[Payment]:
        payments = self._store.filter(lambda payment: payment.booking_id == booking_id)
        return sorted(payments, key=lambda payment: payment.created_at)


class InMemoryIdempotencyStore(IdempotencyStore):
    def __init__(self) -> None:
        self._store: InMemoryStore[str, IdempotencyRecord] = InMemoryStore()

    def find(self, key: str) -> IdempotencyRecord | None:
        return self._store.get(key)

    def save(self, key: str, record: IdempotencyRecord) -> None:
        self._store.put(key, record)
