import threading
from collections.abc import Callable


class InMemoryStore[K, V]:
    """Thread-safe dict shared by the in-memory repositories.

    The lock only protects the dict structure. Business-level atomicity, like
    check-then-reserve, is the application layer's job via ``LockProvider``.
    """

    def __init__(self) -> None:
        self._items: dict[K, V] = {}
        self._lock = threading.RLock()

    def put(self, key: K, value: V) -> None:
        with self._lock:
            self._items[key] = value

    def get(self, key: K) -> V | None:
        with self._lock:
            return self._items.get(key)

    def filter(self, predicate: Callable[[V], bool]) -> list[V]:
        with self._lock:
            return [item for item in self._items.values() if predicate(item)]
