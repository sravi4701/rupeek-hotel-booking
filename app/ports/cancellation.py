from abc import ABC, abstractmethod
from datetime import datetime

from app.domain.booking.booking import Booking
from app.domain.common.money import Money


class CancellationPolicy(ABC):
    """Decides how much of a paid booking is refunded when it is cancelled at a given time."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def description(self) -> str: ...

    @abstractmethod
    def refund_for(self, booking: Booking, cancelled_at: datetime) -> Money: ...
