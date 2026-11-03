from datetime import date, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.api.conftest import create_owner, property_payload

CHECK_IN = date.today() + timedelta(days=30)
CHECK_OUT = CHECK_IN + timedelta(days=2)
SEARCH = {
    "city": "Bengaluru",
    "check_in": CHECK_IN.isoformat(),
    "check_out": CHECK_OUT.isoformat(),
    "guests": 3,  # only the single-unit Suite fits
}


@pytest.fixture
def hotel(client: TestClient) -> dict[str, Any]:
    owner_id = create_owner(client)
    payload = property_payload(cancellation_policy="moderate")
    prop: dict[str, Any] = client.post(f"/owners/{owner_id}/properties", json=payload).json()
    return prop


def _book_suite(client: TestClient, hotel: dict[str, Any]) -> dict[str, Any]:
    suite = next(rt for rt in hotel["room_types"] if rt["name"] == "Suite")
    response = client.post(
        "/bookings",
        json={
            "property_id": hotel["id"],
            "room_type_id": suite["id"],
            "guest_name": "Asha",
            "check_in": CHECK_IN.isoformat(),
            "check_out": CHECK_OUT.isoformat(),
            "guests": 3,
        },
    )
    assert response.status_code == 201, response.text
    booking: dict[str, Any] = response.json()
    return booking


def test_full_lifecycle_book_pay_cancel_rebook(client: TestClient, hotel: dict[str, Any]) -> None:
    booking = _book_suite(client, hotel)
    assert booking["cancellation_policy"] == "moderate"
    assert client.get("/properties/search", params=SEARCH).json() == []

    paid = client.post(
        f"/bookings/{booking['id']}/payments",
        json={"method": "upi", "details": {"vpa": "asha@okicici"}},
    )
    assert paid.json()["booking_status"] == "confirmed"

    cancelled = client.post(f"/bookings/{booking['id']}/cancel")

    assert cancelled.status_code == 200
    body = cancelled.json()
    assert body["status"] == "cancelled"
    assert body["refund_amount"] == body["total_price"]  # 30 days notice: full refund
    [payment] = client.get(f"/bookings/{booking['id']}/payments").json()
    assert payment["status"] == "refunded"
    assert payment["refunded_amount"] == body["total_price"]

    assert len(client.get("/properties/search", params=SEARCH).json()) == 1
    assert _book_suite(client, hotel)["status"] == "pending_payment"


def test_cancel_unpaid_booking(client: TestClient, hotel: dict[str, Any]) -> None:
    booking = _book_suite(client, hotel)

    body = client.post(f"/bookings/{booking['id']}/cancel").json()

    assert body["status"] == "cancelled"
    assert body["refund_amount"] == "0.00"


def test_double_cancel_is_409(client: TestClient, hotel: dict[str, Any]) -> None:
    booking = _book_suite(client, hotel)
    client.post(f"/bookings/{booking['id']}/cancel")

    response = client.post(f"/bookings/{booking['id']}/cancel")

    assert response.status_code == 409


def test_unknown_policy_rejected_at_onboarding(client: TestClient) -> None:
    owner_id = create_owner(client)

    response = client.post(
        f"/owners/{owner_id}/properties", json=property_payload(cancellation_policy="lenient")
    )

    assert response.status_code == 422


def test_cancel_unknown_booking_is_404(client: TestClient) -> None:
    assert client.post("/bookings/ghost/cancel").status_code == 404
