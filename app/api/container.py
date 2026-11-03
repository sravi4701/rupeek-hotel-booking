"""Composition root: the one place that picks concrete implementations for each port.

Application services are built from the ports in ``__post_init__``. Tests can
override any port (e.g. ``Container(clock=FixedClock(...))``) and the services
pick it up.
"""

from dataclasses import dataclass, field

from app.application.booking_service import BookingService
from app.application.inventory_allocator import InventoryAllocator
from app.application.onboarding_service import OnboardingService
from app.application.payment_service import PaymentService
from app.application.search_service import SearchService
from app.infrastructure.clock import SystemClock
from app.infrastructure.gateways.mock_payment_gateway import MockPaymentGateway
from app.infrastructure.locks import KeyedLockManager
from app.infrastructure.persistence.in_memory.repositories import (
    InMemoryBookingRepository,
    InMemoryIdempotencyStore,
    InMemoryInventoryRepository,
    InMemoryOwnerRepository,
    InMemoryPaymentRepository,
    InMemoryPropertyRepository,
)
from app.ports.clock import Clock
from app.ports.locks import LockProvider
from app.ports.payment_gateway import PaymentGateway
from app.ports.pricing import PricingStrategy
from app.ports.repositories import (
    BookingRepository,
    IdempotencyStore,
    InventoryRepository,
    OwnerRepository,
    PaymentRepository,
    PropertyRepository,
)
from app.strategies.payments.registry import PaymentMethodRegistry, default_payment_methods
from app.strategies.pricing.standard import StandardPricing


@dataclass(slots=True)
class Container:
    clock: Clock = field(default_factory=SystemClock)
    locks: LockProvider = field(default_factory=KeyedLockManager)
    pricing: PricingStrategy = field(default_factory=StandardPricing)
    owners: OwnerRepository = field(default_factory=InMemoryOwnerRepository)
    properties: PropertyRepository = field(default_factory=InMemoryPropertyRepository)
    inventory: InventoryRepository = field(default_factory=InMemoryInventoryRepository)
    bookings: BookingRepository = field(default_factory=InMemoryBookingRepository)
    payments: PaymentRepository = field(default_factory=InMemoryPaymentRepository)
    idempotency: IdempotencyStore = field(default_factory=InMemoryIdempotencyStore)
    gateway: PaymentGateway = field(default_factory=MockPaymentGateway)
    payment_methods: PaymentMethodRegistry = field(default_factory=default_payment_methods)

    onboarding: OnboardingService = field(init=False)
    search: SearchService = field(init=False)
    allocator: InventoryAllocator = field(init=False)
    booking: BookingService = field(init=False)
    payment: PaymentService = field(init=False)

    def __post_init__(self) -> None:
        self.onboarding = OnboardingService(self.owners, self.properties, self.inventory)
        self.search = SearchService(self.properties, self.inventory, self.pricing, self.clock)
        self.allocator = InventoryAllocator(self.inventory, self.locks)
        self.booking = BookingService(
            self.properties, self.bookings, self.allocator, self.pricing, self.clock
        )
        self.payment = PaymentService(
            self.bookings,
            self.payments,
            self.idempotency,
            self.payment_methods,
            self.gateway,
            self.locks,
            self.clock,
        )
