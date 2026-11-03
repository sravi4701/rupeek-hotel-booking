import os
from dataclasses import dataclass

_TRUTHY = {"1", "true", "yes", "on"}


@dataclass(frozen=True, slots=True)
class Settings:
    pricing: str = "standard"
    seed_demo_data: bool = False

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            pricing=os.getenv("PRICING_STRATEGY", "standard"),
            seed_demo_data=os.getenv("SEED_DEMO_DATA", "").lower() in _TRUTHY,
        )
