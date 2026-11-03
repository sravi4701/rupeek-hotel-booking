from dataclasses import dataclass

from app.domain.common.date_range import DateRange
from app.ports.locks import LockProvider
from app.ports.repositories import InventoryRepository


@dataclass(slots=True)
class InventoryAllocator:
    """The only code that changes room inventory.

    Each reserve or release runs as an atomic read-check-write under a lock for
    that (property, room type). Concurrent requests for the last unit therefore
    can't both succeed, and different room types never block each other.
    """

    inventory: InventoryRepository
    locks: LockProvider

    def reserve(self, property_id: str, room_type_id: str, stay: DateRange, units: int) -> None:
        with self.locks.hold(self._key(property_id, room_type_id)):
            room_inventory = self.inventory.get(property_id, room_type_id)
            room_inventory.reserve(stay, units)
            self.inventory.save(room_inventory)

    def release(self, property_id: str, room_type_id: str, stay: DateRange, units: int) -> None:
        with self.locks.hold(self._key(property_id, room_type_id)):
            room_inventory = self.inventory.get(property_id, room_type_id)
            room_inventory.release(stay, units)
            self.inventory.save(room_inventory)

    @staticmethod
    def _key(property_id: str, room_type_id: str) -> tuple[str, str, str]:
        return ("inventory", property_id, room_type_id)
