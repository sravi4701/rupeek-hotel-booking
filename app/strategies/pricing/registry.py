from collections.abc import Callable

from app.ports.pricing import PricingStrategy
from app.strategies.pricing.standard import StandardPricing
from app.strategies.pricing.weekend_surcharge import WeekendSurchargePricing

PRICING_STRATEGIES: dict[str, Callable[[], PricingStrategy]] = {
    "standard": StandardPricing,
    "weekend": WeekendSurchargePricing,
}


def pricing_strategy(name: str) -> PricingStrategy:
    """Resolve a strategy by name. Used once at startup, so a typo fails fast."""
    try:
        return PRICING_STRATEGIES[name]()
    except KeyError:
        raise ValueError(
            f"Unknown pricing strategy '{name}'; choose one of {sorted(PRICING_STRATEGIES)}"
        ) from None
