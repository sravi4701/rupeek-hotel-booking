from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.api.conftest import create_owner, property_payload


def test_register_owner(client: TestClient) -> None:
    response = client.post("/owners", json={"name": "Solo Inn"})

    assert response.status_code == 201
    body = response.json()
    assert body["account_type"] == "individual"
    assert body["property_ids"] == []
    assert client.get(f"/owners/{body['id']}").json() == body


def test_onboard_property_and_fetch_it(client: TestClient) -> None:
    owner_id = create_owner(client)

    created = client.post(f"/owners/{owner_id}/properties", json=property_payload())

    assert created.status_code == 201
    prop = created.json()
    assert prop["owner_id"] == owner_id
    assert prop["location"]["city"] == "Bengaluru"
    assert {rt["name"] for rt in prop["room_types"]} == {"Deluxe", "Suite"}
    assert prop["room_types"][0]["nightly_rate"] == "4000.00"
    assert client.get(f"/properties/{prop['id']}").json() == prop


def test_chain_lists_all_its_properties(client: TestClient) -> None:
    owner_id = create_owner(client)
    for name in ("Sunrise Koramangala", "Sunrise Indiranagar"):
        client.post(f"/owners/{owner_id}/properties", json=property_payload(name))

    listed = client.get(f"/owners/{owner_id}/properties").json()

    assert {p["name"] for p in listed} == {"Sunrise Koramangala", "Sunrise Indiranagar"}
    assert len(client.get(f"/owners/{owner_id}").json()["property_ids"]) == 2


@pytest.mark.parametrize(
    "overrides",
    [
        {"star_rating": 6},
        {"room_types": []},
        {"amenities": ["jacuzzi"]},
        {"room_types": [{"name": "X", "max_occupancy": 0, "total_units": 1, "nightly_rate": 1}]},
        {"room_types": [{"name": "X", "max_occupancy": 1, "total_units": 1, "nightly_rate": 0}]},
    ],
    ids=["stars", "no-rooms", "unknown-amenity", "zero-occupancy", "zero-rate"],
)
def test_rejects_invalid_property(client: TestClient, overrides: dict[str, Any]) -> None:
    owner_id = create_owner(client)

    response = client.post(f"/owners/{owner_id}/properties", json=property_payload(**overrides))

    assert response.status_code == 422


def test_duplicate_room_type_names_rejected_by_domain(client: TestClient) -> None:
    owner_id = create_owner(client)
    room = {"name": "Deluxe", "max_occupancy": 2, "total_units": 1, "nightly_rate": "100"}

    response = client.post(
        f"/owners/{owner_id}/properties", json=property_payload(room_types=[room, room])
    )

    assert response.status_code == 422
    assert response.json()["error"] == "DomainValidationError"


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/owners/ghost"),
        ("get", "/owners/ghost/properties"),
        ("post", "/owners/ghost/properties"),
        ("get", "/properties/ghost"),
    ],
)
def test_unknown_ids_return_404(client: TestClient, method: str, path: str) -> None:
    kwargs = {"json": property_payload()} if method == "post" else {}

    response = client.request(method, path, **kwargs)

    assert response.status_code == 404
