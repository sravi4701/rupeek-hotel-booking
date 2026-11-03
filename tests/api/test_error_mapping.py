from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from app.domain.common.exceptions import (
    DomainError,
    DomainValidationError,
    InsufficientInventoryError,
    InvalidStateTransitionError,
    NotFoundError,
)
from app.main import create_app

CASES = [
    (DomainValidationError("bad input"), 422),
    (NotFoundError("Booking", "b1"), 404),
    (InsufficientInventoryError("sold out"), 409),
    (InvalidStateTransitionError("Booking", "cancelled", "confirmed"), 409),
    (DomainError("generic"), 400),
]


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    for index, (error, _) in enumerate(CASES):
        app.add_api_route(f"/_raise/{index}", _raiser(error))
    return TestClient(app)


def _raiser(error: DomainError) -> Callable[[], None]:
    def raise_error() -> None:
        raise error

    return raise_error


@pytest.mark.parametrize(("index", "case"), list(enumerate(CASES)))
def test_domain_errors_map_to_http_status(
    client: TestClient, index: int, case: tuple[DomainError, int]
) -> None:
    error, expected_status = case

    response = client.get(f"/_raise/{index}")

    assert response.status_code == expected_status
    assert response.json() == {"error": type(error).__name__, "message": str(error)}
