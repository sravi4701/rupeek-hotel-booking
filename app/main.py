from fastapi import FastAPI

from app.api.container import Container
from app.api.errors import register_exception_handlers
from app.api.routers import bookings, owners, properties


def create_app(container: Container | None = None) -> FastAPI:
    app = FastAPI(
        title="Hotel Booking Service",
        description="Discover, onboard, book, pay for and cancel hotel stays.",
        version="0.1.0",
    )
    app.state.container = container or Container()
    register_exception_handlers(app)

    app.include_router(owners.router)
    app.include_router(properties.router)
    app.include_router(bookings.router)

    @app.get("/health", tags=["ops"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
