from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import build_container, create_app
from app.strategies.pricing.weekend_surcharge import WeekendSurchargePricing


def test_settings_read_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PRICING_STRATEGY", "weekend")
    monkeypatch.setenv("SEED_DEMO_DATA", "true")

    assert Settings.from_env() == Settings(pricing="weekend", seed_demo_data=True)


def test_defaults_are_standard_pricing_and_empty_store(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PRICING_STRATEGY", raising=False)
    monkeypatch.delenv("SEED_DEMO_DATA", raising=False)

    assert Settings.from_env() == Settings()


def test_pricing_strategy_is_selected_by_config() -> None:
    container = build_container(Settings(pricing="weekend"))

    assert isinstance(container.pricing, WeekendSurchargePricing)
    assert isinstance(container.booking.pricing, WeekendSurchargePricing)
    assert isinstance(container.search.pricing, WeekendSurchargePricing)


def test_seeded_app_is_searchable_end_to_end() -> None:
    client = TestClient(create_app(build_container(Settings(seed_demo_data=True))))
    check_in = date.today() + timedelta(days=14)
    params = {
        "city": "Bengaluru",
        "check_in": check_in.isoformat(),
        "check_out": (check_in + timedelta(days=2)).isoformat(),
        "guests": 2,
    }

    results = client.get("/properties/search", params=params).json()

    assert {r["name"] for r in results} == {
        "Green Nest Homestay",
        "Sunrise Koramangala",
        "Sunrise Indiranagar",
    }
