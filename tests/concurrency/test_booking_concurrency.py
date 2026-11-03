"""Many threads race for the same inventory. Exactly ``capacity`` bookings may win.

The plain in-memory repository hands every thread the same object, and the GIL
then hides the race. These tests use ``DatabaseLikeInventoryRepository``, which
behaves like a real store: each read returns a fresh copy after some latency.
Without locking that produces lost updates. ``test_control_without_locks_oversells``
shows these tests really do catch a missing lock.
"""

import copy
import threading
import time
from collections.abc import Callable, Hashable, Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import date, datetime

from app.api.container import Container
from app.domain.booking.booking import Booking
from app.domain.common.exceptions import InsufficientInventoryError
from app.domain.inventory.room_inventory import RoomInventory
from app.infrastructure.clock import FixedClock
from app.infrastructure.persistence.in_memory.repositories import InMemoryInventoryRepository
from app.ports.locks import LockProvider
from tests.factories import NOW, booking_request, onboard_hotel, stay

THREADS = 50
FEB_1_4 = stay(date(2027, 2, 1), date(2027, 2, 4))


class DatabaseLikeInventoryRepository(InMemoryInventoryRepository):
    def find(self, property_id: str, room_type_id: str) -> RoomInventory | None:
        stored = super().find(property_id, room_type_id)
        time.sleep(0.002)  # simulated round-trip
        return copy.deepcopy(stored)


class NoLocks(LockProvider):
    @contextmanager
    def hold(self, key: Hashable) -> Iterator[None]:
        yield


def _container(now: datetime = NOW) -> Container:
    return Container(clock=FixedClock(now), inventory=DatabaseLikeInventoryRepository())


def _race(attempt: Callable[[int], Booking]) -> list[Booking]:
    """Start every attempt at the same moment. Returns the bookings that succeeded."""
    barrier = threading.Barrier(THREADS)

    def run(index: int) -> Booking | None:
        barrier.wait()
        try:
            return attempt(index)
        except InsufficientInventoryError:
            return None

    with ThreadPoolExecutor(max_workers=THREADS) as pool:
        return [b for b in pool.map(run, range(THREADS)) if b is not None]


def _book_same_stay(container: Container, units: int) -> list[Booking]:
    hotel = onboard_hotel(container, units=units)
    return _race(
        lambda i: container.booking.create(booking_request(hotel, FEB_1_4, guest_name=f"g{i}"))
    )


def test_only_available_units_are_sold_under_contention() -> None:
    container = _container()

    successes = _book_same_stay(container, units=3)

    assert len(successes) == 3
    [prop] = container.properties.find_by_location("Bengaluru")
    [room_type_id] = prop.room_types
    assert container.inventory.get(prop.id, room_type_id).available_units(FEB_1_4) == 0


def test_overlapping_ranges_race_without_overselling_any_night() -> None:
    container = _container()
    hotel = onboard_hotel(container, units=1)
    # Each thread wants a 2-night window inside Feb 1-10, and many windows overlap.
    windows = [stay(date(2027, 2, 1 + i % 8), date(2027, 2, 3 + i % 8)) for i in range(THREADS)]

    successes = _race(
        lambda i: container.booking.create(booking_request(hotel, windows[i], guest_name=f"g{i}"))
    )

    assert successes
    for i, a in enumerate(successes):
        for b in successes[i + 1 :]:
            assert not a.stay.overlaps(b.stay), (a.stay, b.stay)


def test_control_without_locks_oversells() -> None:
    """Shows the tests above can fail: switch locking off and the race oversells."""
    container = _container()
    container.allocator.locks = NoLocks()

    successes = _book_same_stay(container, units=3)

    assert len(successes) > 3
