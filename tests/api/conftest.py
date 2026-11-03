from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.container import Container
from app.main import create_app


@pytest.fixture
def container() -> Container:
    return Container()


@pytest.fixture
def client(container: Container) -> TestClient:
    return TestClient(create_app(container))


def property_payload(name: str = "Sunrise Koramangala", **overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "name": name,
        "city": "Bengaluru",
        "locality": "Koramangala",
        "star_rating": 4,
        "amenities": ["wifi", "parking"],
        "room_types": [
            {"name": "Deluxe", "max_occupancy": 2, "total_units": 5, "nightly_rate": "4000"},
            {"name": "Suite", "max_occupancy": 4, "total_units": 1, "nightly_rate": "9000"},
        ],
    }
    payload.update(overrides)
    return payload


def create_owner(client: TestClient, name: str = "Sunrise Hotels", kind: str = "chain") -> str:
    response = client.post("/owners", json={"name": name, "account_type": kind})
    assert response.status_code == 201, response.text
    owner_id: str = response.json()["id"]
    return owner_id
