import pytest

from app.domain.common.exceptions import NotFoundError
from app.domain.common.money import Money
from app.domain.inventory.room_inventory import RoomInventory
from app.domain.property.location import Location
from app.domain.property.owner import OwnerAccount
from app.domain.property.property import Property
from app.domain.property.room_type import RoomType
from app.infrastructure.persistence.in_memory.repositories import (
    InMemoryInventoryRepository,
    InMemoryOwnerRepository,
    InMemoryPropertyRepository,
)


def _property(owner_id: str, city: str, locality: str) -> Property:
    room = RoomType(name="Std", max_occupancy=2, total_units=1, nightly_rate=Money.of(1000))
    return Property.create(
        owner_id=owner_id,
        name=f"{city}-{locality}",
        location=Location(city, locality),
        star_rating=3,
        room_types=[room],
    )


def test_find_returns_none_and_get_raises_for_missing_id() -> None:
    repo = InMemoryOwnerRepository()

    assert repo.find("nope") is None
    with pytest.raises(NotFoundError, match="Owner 'nope' not found"):
        repo.get("nope")


def test_save_then_get_round_trips() -> None:
    repo = InMemoryOwnerRepository()
    owner = OwnerAccount(name="Taj Group")

    repo.save(owner)

    assert repo.get(owner.id) is owner


class TestPropertyQueries:
    @pytest.fixture
    def repo(self) -> InMemoryPropertyRepository:
        repo = InMemoryPropertyRepository()
        for prop in [
            _property("o1", "Bengaluru", "Koramangala"),
            _property("o1", "Bengaluru", "Indiranagar"),
            _property("o2", "Goa", "Calangute"),
        ]:
            repo.save(prop)
        return repo

    def test_list_by_owner(self, repo: InMemoryPropertyRepository) -> None:
        assert {p.name for p in repo.list_by_owner("o1")} == {
            "Bengaluru-Koramangala",
            "Bengaluru-Indiranagar",
        }

    def test_find_by_city(self, repo: InMemoryPropertyRepository) -> None:
        assert len(repo.find_by_location("bengaluru")) == 2

    def test_find_by_city_and_locality(self, repo: InMemoryPropertyRepository) -> None:
        [match] = repo.find_by_location("Bengaluru", "indiranagar")

        assert match.name == "Bengaluru-Indiranagar"


def test_inventory_is_keyed_by_property_and_room_type() -> None:
    repo = InMemoryInventoryRepository()
    inventory = RoomInventory(property_id="p1", room_type_id="rt1", total_units=3)

    repo.save(inventory)

    assert repo.get("p1", "rt1") is inventory
    assert repo.find("p1", "rt2") is None
    with pytest.raises(NotFoundError):
        repo.get("p2", "rt1")
