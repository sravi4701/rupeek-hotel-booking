from datetime import datetime, timedelta

from app.ports.clock import Clock


class SystemClock(Clock):
    def now(self) -> datetime:
        return datetime.now()


class FixedClock(Clock):
    """Deterministic clock for tests and demos. Time only moves when told to."""

    def __init__(self, at: datetime) -> None:
        self._now = at

    def now(self) -> datetime:
        return self._now

    def advance(self, delta: timedelta) -> None:
        self._now += delta
