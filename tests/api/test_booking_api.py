from datetime import date, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.api.conftest import create_owner, property_payload

CHECK_IN = date.today() + timedelta(days=30)
CHECK_OUT = CHECK_IN + timedelta(days=2)


@pytest.fixture
def hotel(client: TestClient) -> dict[str, Any]:
    owner_id = create_owner(client)
    response = client.post(f"/owners/{owner_id}/properties", json=property_payload())
    prop: dict[str, Any] = response.json()
    return prop


def _room_type_id(hotel: dict[str, Any], name: str) -> str:
    return next(rt["id"] for rt in hotel["room_types"] if rt["name"] == name)


def _book(client: TestClient, hotel: dict[str, Any], **overrides: Any) -> Any:
    body: dict[str, Any] = {
        "property_id": hotel["id"],
        "room_type_id": _room_type_id(hotel, "Suite"),  # 1 unit
        "guest_name": "Asha",
        "check_in": CHECK_IN.isoformat(),
        "check_out": CHECK_OUT.isoformat(),
        "guests": 2,
    }
    body.update(overrides)
    return client.post("/bookings", json=body)


def test_create_and_fetch_booking(client: TestClient, hotel: dict[str, Any]) -> None:
    response = _book(client, hotel)

    assert response.status_code == 201
    booking = response.json()
    assert booking["status"] == "pending_payment"
    assert booking["nights"] == 2
    assert booking["total_price"] == "18000.00"
    assert booking["payment_id"] is None
    assert client.get(f"/bookings/{booking['id']}").json() == booking


def test_second_booking_for_last_unit_conflicts(client: TestClient, hotel: dict[str, Any]) -> None:
    assert _book(client, hotel).status_code == 201

    response = _book(client, hotel, guest_name="Ravi")

    assert response.status_code == 409
    assert response.json()["error"] == "InsufficientInventoryError"


def test_sold_out_room_type_drops_out_of_search(client: TestClient, hotel: dict[str, Any]) -> None:
    _book(client, hotel)

    results = client.get(
        "/properties/search",
        params={
            "city": "Bengaluru",
            "check_in": CHECK_IN.isoformat(),
            "check_out": CHECK_OUT.isoformat(),
            "guests": 2,
        },
    ).json()

    [result] = results
    assert {o["room_type_name"] for o in result["offers"]} == {"Deluxe"}


@pytest.mark.parametrize(
    ("overrides", "status"),
    [
        ({"guests": 5}, 422),
        ({"check_out": CHECK_IN.isoformat()}, 422),
        ({"check_in": (date.today() - timedelta(days=1)).isoformat()}, 422),
        ({"guest_name": ""}, 422),
        ({"property_id": "ghost"}, 404),
        ({"room_type_id": "ghost"}, 404),
    ],
    ids=["over-capacity", "bad-dates", "past", "no-name", "no-property", "no-room-type"],
)
def test_rejects_invalid_bookings(
    client: TestClient, hotel: dict[str, Any], overrides: dict[str, Any], status: int
) -> None:
    assert _book(client, hotel, **overrides).status_code == status


def test_unknown_booking_is_404(client: TestClient) -> None:
    assert client.get("/bookings/ghost").status_code == 404
