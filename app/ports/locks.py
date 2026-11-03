from abc import ABC, abstractmethod
from collections.abc import Hashable
from contextlib import AbstractContextManager


class LockProvider(ABC):
    """Mutual exclusion per key (e.g. one room type's inventory).

    The in-process implementation uses threading locks. With several service
    instances this would be backed by DB row locks or a distributed lock.
    """

    @abstractmethod
    def hold(self, key: Hashable) -> AbstractContextManager[None]: ...
