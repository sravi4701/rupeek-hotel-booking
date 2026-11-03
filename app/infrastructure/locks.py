import threading
from collections.abc import Hashable, Iterator
from contextlib import contextmanager

from app.ports.locks import LockProvider


class KeyedLockManager(LockProvider):
    """One lock per key, created on first use.

    Bookings for different room types never wait on each other. Only callers
    with the same key are serialised.
    """

    def __init__(self) -> None:
        self._locks: dict[Hashable, threading.Lock] = {}
        self._registry_lock = threading.Lock()

    def _lock_for(self, key: Hashable) -> threading.Lock:
        with self._registry_lock:
            return self._locks.setdefault(key, threading.Lock())

    @contextmanager
    def hold(self, key: Hashable) -> Iterator[None]:
        with self._lock_for(key):
            yield
