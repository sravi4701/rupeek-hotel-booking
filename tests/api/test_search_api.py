from datetime import date, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.api.conftest import create_owner, property_payload

CHECK_IN = date.today() + timedelta(days=30)
CHECK_OUT = CHECK_IN + timedelta(days=2)


def _search(client: TestClient, **params: Any) -> Any:
    query: dict[str, Any] = {
        "city": "Bengaluru",
        "check_in": CHECK_IN.isoformat(),
        "check_out": CHECK_OUT.isoformat(),
        "guests": 2,
    }
    query.update(params)
    return client.get("/properties/search", params=query)


@pytest.fixture
def seeded(client: TestClient) -> TestClient:
    owner_id = create_owner(client)
    client.post(
        f"/owners/{owner_id}/properties",
        json=property_payload("Budget Stay", star_rating=2, amenities=["wifi"]),
    )
    client.post(
        f"/owners/{owner_id}/properties",
        json=property_payload("Grand Palace", star_rating=5, amenities=["wifi", "pool"]),
    )
    client.post(f"/owners/{owner_id}/properties", json=property_payload("Sea Breeze", city="Goa"))
    return client


def test_returns_available_properties_with_priced_offers(seeded: TestClient) -> None:
    response = _search(seeded)

    assert response.status_code == 200
    results = response.json()
    assert {r["name"] for r in results} == {"Budget Stay", "Grand Palace"}
    deluxe = results[0]["offers"][0]
    assert deluxe["room_type_name"] == "Deluxe"
    assert deluxe["price_per_room_night"] == "4000.00"
    assert deluxe["total_price"] == "8000.00"


def test_suite_offered_only_when_guests_need_it(seeded: TestClient) -> None:
    results = _search(seeded, guests=4).json()

    assert results
    assert all(o["room_type_name"] == "Suite" for r in results for o in r["offers"])


@pytest.mark.parametrize(
    ("params", "expected"),
    [
        ({"min_rating": 4}, {"Grand Palace"}),
        ({"amenities": ["wifi", "pool"]}, {"Grand Palace"}),
        ({"max_price": "3000"}, set()),
        ({"min_price": "3500", "max_price": "4500"}, {"Budget Stay", "Grand Palace"}),
        ({"locality": "koramangala"}, {"Budget Stay", "Grand Palace"}),
    ],
)
def test_filters(seeded: TestClient, params: dict[str, Any], expected: set[str]) -> None:
    assert {r["name"] for r in _search(seeded, **params).json()} == expected


@pytest.mark.parametrize(
    "params",
    [
        {"check_out": CHECK_IN.isoformat()},
        {"check_in": (date.today() - timedelta(days=1)).isoformat()},
        {"guests": 0},
        {"min_price": "5000", "max_price": "1000"},
        {"min_rating": 6},
        {"amenities": ["jacuzzi"]},
    ],
    ids=["checkout-before-checkin", "past", "no-guests", "inverted-price", "rating", "amenity"],
)
def test_rejects_invalid_queries(seeded: TestClient, params: dict[str, Any]) -> None:
    assert _search(seeded, **params).status_code == 422
