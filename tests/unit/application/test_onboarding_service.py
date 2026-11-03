from decimal import Decimal

import pytest

from app.application.onboarding_service import (
    OnboardingService,
    PropertyDetails,
    RoomTypeDetails,
)
from app.domain.common.exceptions import DomainValidationError, NotFoundError
from app.domain.property.amenity import Amenity
from app.domain.property.owner import AccountType
from app.infrastructure.persistence.in_memory.repositories import (
    InMemoryInventoryRepository,
    InMemoryOwnerRepository,
    InMemoryPropertyRepository,
)


def _details(name: str = "Sunrise", **overrides: object) -> PropertyDetails:
    kwargs: dict[str, object] = {
        "name": name,
        "city": "Bengaluru",
        "locality": "Koramangala",
        "star_rating": 4,
        "amenities": frozenset({Amenity.WIFI}),
        "room_types": [
            RoomTypeDetails("Deluxe", max_occupancy=2, total_units=5, nightly_rate=Decimal(4000)),
            RoomTypeDetails("Suite", max_occupancy=4, total_units=2, nightly_rate=Decimal(9000)),
        ],
    }
    kwargs.update(overrides)
    return PropertyDetails(**kwargs)  # type: ignore[arg-type]


@pytest.fixture
def inventory() -> InMemoryInventoryRepository:
    return InMemoryInventoryRepository()


@pytest.fixture
def service(inventory: InMemoryInventoryRepository) -> OnboardingService:
    return OnboardingService(InMemoryOwnerRepository(), InMemoryPropertyRepository(), inventory)


def test_standalone_property_is_an_owner_with_one_property(service: OnboardingService) -> None:
    owner = service.register_owner("Solo Inn", AccountType.INDIVIDUAL)

    prop = service.onboard_property(owner.id, _details())

    assert service.get_owner(owner.id).property_ids == [prop.id]
    assert prop.owner_id == owner.id


def test_chain_manages_many_properties_under_one_account(service: OnboardingService) -> None:
    chain = service.register_owner("Sunrise Hotels", AccountType.CHAIN)

    first = service.onboard_property(chain.id, _details("Sunrise Koramangala"))
    second = service.onboard_property(chain.id, _details("Sunrise Indiranagar"))

    assert service.get_owner(chain.id).property_ids == [first.id, second.id]
    assert {p.id for p in service.list_properties(chain.id)} == {first.id, second.id}


def test_onboarding_creates_inventory_for_every_room_type(
    service: OnboardingService, inventory: InMemoryInventoryRepository
) -> None:
    owner = service.register_owner("Solo Inn", AccountType.INDIVIDUAL)

    prop = service.onboard_property(owner.id, _details())

    for room_type in prop.room_types.values():
        assert inventory.get(prop.id, room_type.id).total_units == room_type.total_units


def test_onboarding_for_unknown_owner_fails(service: OnboardingService) -> None:
    with pytest.raises(NotFoundError):
        service.onboard_property("ghost", _details())


def test_invalid_property_is_not_persisted(service: OnboardingService) -> None:
    owner = service.register_owner("Solo Inn", AccountType.INDIVIDUAL)

    with pytest.raises(DomainValidationError):
        service.onboard_property(owner.id, _details(star_rating=7))

    assert service.list_properties(owner.id) == []
    assert service.get_owner(owner.id).property_ids == []


def test_listing_properties_of_unknown_owner_is_not_found(service: OnboardingService) -> None:
    with pytest.raises(NotFoundError):
        service.list_properties("ghost")
