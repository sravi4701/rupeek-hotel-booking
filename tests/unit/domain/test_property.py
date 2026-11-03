import pytest

from app.domain.common.exceptions import DomainValidationError, NotFoundError
from app.domain.common.money import Money
from app.domain.property.amenity import Amenity
from app.domain.property.location import Location
from app.domain.property.owner import AccountType, OwnerAccount
from app.domain.property.property import Property
from app.domain.property.room_type import RoomType


def _room(name: str = "Deluxe", occupancy: int = 2, units: int = 5) -> RoomType:
    return RoomType(
        name=name, max_occupancy=occupancy, total_units=units, nightly_rate=Money.of(3000)
    )


def _property(**overrides: object) -> Property:
    kwargs: dict[str, object] = {
        "owner_id": "owner-1",
        "name": "Sea View",
        "location": Location("Goa", "Calangute"),
        "star_rating": 4,
        "room_types": [_room()],
    }
    kwargs.update(overrides)
    return Property.create(**kwargs)  # type: ignore[arg-type]


class TestRoomType:
    def test_capacity_scales_with_rooms(self) -> None:
        room = _room(occupancy=2)

        assert room.can_host(guests=4, rooms=2)
        assert not room.can_host(guests=5, rooms=2)

    @pytest.mark.parametrize(
        "kwargs",
        [{"max_occupancy": 0}, {"total_units": 0}, {"nightly_rate": Money.zero()}, {"name": ""}],
    )
    def test_rejects_invalid_definition(self, kwargs: dict[str, object]) -> None:
        base: dict[str, object] = {
            "name": "Deluxe",
            "max_occupancy": 2,
            "total_units": 1,
            "nightly_rate": Money.of(100),
        }
        with pytest.raises(DomainValidationError):
            RoomType(**(base | kwargs))  # type: ignore[arg-type]


class TestProperty:
    @pytest.mark.parametrize("stars", [0, 6])
    def test_star_rating_bounds(self, stars: int) -> None:
        with pytest.raises(DomainValidationError):
            _property(star_rating=stars)

    def test_requires_room_types(self) -> None:
        with pytest.raises(DomainValidationError):
            _property(room_types=[])

    def test_room_type_names_unique(self) -> None:
        with pytest.raises(DomainValidationError):
            _property(room_types=[_room("Deluxe"), _room("deluxe")])

    def test_room_type_lookup(self) -> None:
        room = _room()
        prop = _property(room_types=[room])

        assert prop.room_type(room.id) is room
        with pytest.raises(NotFoundError):
            prop.room_type("missing")

    def test_amenities_combine_property_and_room(self) -> None:
        room = RoomType(
            name="Suite",
            max_occupancy=2,
            total_units=1,
            nightly_rate=Money.of(9000),
            amenities=frozenset({Amenity.SPA}),
        )
        prop = _property(room_types=[room], amenities=[Amenity.WIFI])

        assert prop.all_amenities_for(room) == {Amenity.WIFI, Amenity.SPA}


class TestOwnerAccount:
    def test_single_and_chain_owners_share_the_same_model(self) -> None:
        solo = OwnerAccount(name="Solo Inn")
        chain = OwnerAccount(name="Taj Group", account_type=AccountType.CHAIN)

        solo.add_property("p1")
        chain.add_property("p2")
        chain.add_property("p3")

        assert solo.property_ids == ["p1"]
        assert chain.property_ids == ["p2", "p3"]

    def test_rejects_duplicate_property(self) -> None:
        owner = OwnerAccount(name="Solo Inn")
        owner.add_property("p1")

        with pytest.raises(DomainValidationError):
            owner.add_property("p1")
