"""Composition root: the one place that picks concrete implementations for each port.

Application services are built from the ports in ``__post_init__``. Tests can
override any port (e.g. ``Container(clock=FixedClock(...))``) and the services
pick it up.
"""

from dataclasses import dataclass, field

from app.application.onboarding_service import OnboardingService
from app.infrastructure.clock import SystemClock
from app.infrastructure.locks import KeyedLockManager
from app.infrastructure.persistence.in_memory.repositories import (
    InMemoryBookingRepository,
    InMemoryInventoryRepository,
    InMemoryOwnerRepository,
    InMemoryPropertyRepository,
)
from app.ports.clock import Clock
from app.ports.locks import LockProvider
from app.ports.repositories import (
    BookingRepository,
    InventoryRepository,
    OwnerRepository,
    PropertyRepository,
)


@dataclass(slots=True)
class Container:
    clock: Clock = field(default_factory=SystemClock)
    locks: LockProvider = field(default_factory=KeyedLockManager)
    owners: OwnerRepository = field(default_factory=InMemoryOwnerRepository)
    properties: PropertyRepository = field(default_factory=InMemoryPropertyRepository)
    inventory: InventoryRepository = field(default_factory=InMemoryInventoryRepository)
    bookings: BookingRepository = field(default_factory=InMemoryBookingRepository)

    onboarding: OnboardingService = field(init=False)

    def __post_init__(self) -> None:
        self.onboarding = OnboardingService(self.owners, self.properties, self.inventory)
