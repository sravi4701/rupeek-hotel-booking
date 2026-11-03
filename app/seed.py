"""Demo data so the API can be explored straight after ``make run``.

Covers a chain with several properties, a standalone hotel, two cities, and
all three cancellation policies.
"""

from decimal import Decimal

from app.api.container import Container
from app.application.onboarding_service import PropertyDetails, RoomTypeDetails
from app.domain.property.amenity import Amenity as A
from app.domain.property.owner import AccountType


def _room(name: str, occupancy: int, units: int, rate: int, *extras: A) -> RoomTypeDetails:
    return RoomTypeDetails(name, occupancy, units, Decimal(rate), frozenset(extras))


def seed_demo_data(container: Container) -> None:
    onboarding = container.onboarding

    chain = onboarding.register_owner("Sunrise Hotels", AccountType.CHAIN)
    onboarding.onboard_property(
        chain.id,
        PropertyDetails(
            name="Sunrise Koramangala",
            city="Bengaluru",
            locality="Koramangala",
            address="80 Feet Road",
            star_rating=4,
            amenities=frozenset({A.WIFI, A.PARKING, A.RESTAURANT, A.GYM}),
            cancellation_policy="flexible",
            room_types=[
                _room("Deluxe", 2, 10, 4500, A.AIR_CONDITIONING),
                _room("Family Suite", 4, 2, 9000, A.AIR_CONDITIONING, A.BREAKFAST),
            ],
        ),
    )
    onboarding.onboard_property(
        chain.id,
        PropertyDetails(
            name="Sunrise Indiranagar",
            city="Bengaluru",
            locality="Indiranagar",
            address="100 Feet Road",
            star_rating=5,
            amenities=frozenset({A.WIFI, A.POOL, A.SPA, A.RESTAURANT}),
            cancellation_policy="moderate",
            room_types=[
                _room("Premier King", 2, 6, 8000, A.AIR_CONDITIONING, A.BREAKFAST),
                _room("Presidential Suite", 4, 1, 25000, A.AIR_CONDITIONING, A.BREAKFAST),
            ],
        ),
    )
    onboarding.onboard_property(
        chain.id,
        PropertyDetails(
            name="Sunrise Calangute",
            city="Goa",
            locality="Calangute",
            star_rating=4,
            amenities=frozenset({A.WIFI, A.POOL, A.PET_FRIENDLY}),
            cancellation_policy="flexible",
            room_types=[_room("Sea View", 3, 8, 6500, A.AIR_CONDITIONING)],
        ),
    )

    standalone = onboarding.register_owner("Asha Homestays", AccountType.INDIVIDUAL)
    onboarding.onboard_property(
        standalone.id,
        PropertyDetails(
            name="Green Nest Homestay",
            city="Bengaluru",
            locality="Koramangala",
            star_rating=3,
            amenities=frozenset({A.WIFI, A.BREAKFAST}),
            cancellation_policy="non_refundable",
            room_types=[_room("Garden Room", 2, 1, 2200)],
        ),
    )
