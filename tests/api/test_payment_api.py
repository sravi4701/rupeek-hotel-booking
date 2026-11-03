from datetime import date, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.api.conftest import create_owner, property_payload

CHECK_IN = date.today() + timedelta(days=30)
GOOD_CARD = {"method": "card", "details": {"card_number": "4242424242424242", "cvv": "123"}}
DECLINED_CARD = {"method": "card", "details": {"card_number": "4000000000000002", "cvv": "123"}}


@pytest.fixture
def booking_id(client: TestClient) -> str:
    owner_id = create_owner(client)
    hotel = client.post(f"/owners/{owner_id}/properties", json=property_payload()).json()
    response = client.post(
        "/bookings",
        json={
            "property_id": hotel["id"],
            "room_type_id": hotel["room_types"][0]["id"],
            "guest_name": "Asha",
            "check_in": CHECK_IN.isoformat(),
            "check_out": (CHECK_IN + timedelta(days=2)).isoformat(),
            "guests": 2,
        },
    )
    booking_id: str = response.json()["id"]
    return booking_id


def _pay(client: TestClient, booking_id: str, body: dict[str, Any], key: str | None = None) -> Any:
    headers = {"Idempotency-Key": key} if key else {}
    return client.post(f"/bookings/{booking_id}/payments", json=body, headers=headers)


def test_successful_payment_confirms_booking(client: TestClient, booking_id: str) -> None:
    response = _pay(client, booking_id, GOOD_CARD)

    assert response.status_code == 201
    body = response.json()
    assert body["booking_status"] == "confirmed"
    assert body["payment"]["status"] == "succeeded"
    assert body["payment"]["instrument"] == "card ****4242"
    assert body["payment"]["amount"] == "8000.00"
    assert client.get(f"/bookings/{booking_id}").json()["status"] == "confirmed"


def test_declined_payment_returns_402_and_allows_retry(client: TestClient, booking_id: str) -> None:
    declined = _pay(client, booking_id, DECLINED_CARD)

    assert declined.status_code == 402
    assert declined.json()["booking_status"] == "pending_payment"

    upi = {"method": "upi", "details": {"vpa": "asha@okhdfc"}}
    assert _pay(client, booking_id, upi).status_code == 201

    attempts = client.get(f"/bookings/{booking_id}/payments").json()
    assert [a["status"] for a in attempts] == ["failed", "succeeded"]


def test_idempotent_replay(client: TestClient, booking_id: str) -> None:
    first = _pay(client, booking_id, GOOD_CARD, key="abc")

    replay = _pay(client, booking_id, GOOD_CARD, key="abc")

    assert replay.status_code == 201
    assert replay.headers["Idempotent-Replayed"] == "true"
    assert replay.json()["payment"]["id"] == first.json()["payment"]["id"]
    assert len(client.get(f"/bookings/{booking_id}/payments").json()) == 1


def test_key_reuse_with_different_body_is_409(client: TestClient, booking_id: str) -> None:
    _pay(client, booking_id, DECLINED_CARD, key="abc")

    response = _pay(client, booking_id, GOOD_CARD, key="abc")

    assert response.status_code == 409
    assert response.json()["error"] == "IdempotencyConflictError"


def test_paying_confirmed_booking_again_is_409(client: TestClient, booking_id: str) -> None:
    _pay(client, booking_id, GOOD_CARD)

    assert _pay(client, booking_id, GOOD_CARD).status_code == 409


@pytest.mark.parametrize(
    ("body", "status"),
    [
        ({"method": "bitcoin", "details": {}}, 422),
        ({"method": "card", "details": {"card_number": "1"}}, 422),
        ({"method": "wallet", "details": {"provider": "paytm"}}, 422),
        ({"details": {}}, 422),
    ],
    ids=["unknown-method", "bad-card", "missing-phone", "no-method"],
)
def test_rejects_invalid_payment_requests(
    client: TestClient, booking_id: str, body: dict[str, Any], status: int
) -> None:
    assert _pay(client, booking_id, body).status_code == status


def test_unknown_booking_is_404(client: TestClient) -> None:
    assert _pay(client, "ghost", GOOD_CARD).status_code == 404
    assert client.get("/bookings/ghost/payments").status_code == 404
