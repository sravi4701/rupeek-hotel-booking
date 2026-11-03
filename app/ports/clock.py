from abc import ABC, abstractmethod
from datetime import date, datetime


class Clock(ABC):
    """Time source for time-based rules (past dates, cancellation windows); fixable in tests."""

    @abstractmethod
    def now(self) -> datetime: ...

    def today(self) -> date:
        return self.now().date()
