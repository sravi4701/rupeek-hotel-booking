from fastapi import FastAPI

from app.api.container import Container
from app.api.errors import register_exception_handlers
from app.api.routers import bookings, owners, payments, properties
from app.config import Settings
from app.seed import seed_demo_data
from app.strategies.pricing.registry import pricing_strategy


def build_container(settings: Settings) -> Container:
    container = Container(pricing=pricing_strategy(settings.pricing))
    if settings.seed_demo_data:
        seed_demo_data(container)
    return container


def create_app(container: Container | None = None) -> FastAPI:
    app = FastAPI(
        title="Hotel Booking Service",
        description=(
            "Discover, onboard, book, pay for and cancel hotel stays. "
            "Typical flow: search -> POST /bookings -> POST /bookings/{id}/payments "
            "-> (optionally) POST /bookings/{id}/cancel."
        ),
        version="1.0.0",
    )
    app.state.container = container or build_container(Settings.from_env())
    register_exception_handlers(app)

    app.include_router(owners.router)
    app.include_router(properties.router)
    app.include_router(bookings.router)
    app.include_router(payments.router)

    @app.get("/health", tags=["ops"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
