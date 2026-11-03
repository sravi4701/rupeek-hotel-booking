from typing import Annotated, cast

from fastapi import Depends, Request

from app.api.container import Container
from app.application.booking_service import BookingService
from app.application.onboarding_service import OnboardingService
from app.application.payment_service import PaymentService
from app.application.search_service import SearchService


def get_container(request: Request) -> Container:
    return cast(Container, request.app.state.container)


ContainerDep = Annotated[Container, Depends(get_container)]


def get_onboarding_service(container: ContainerDep) -> OnboardingService:
    return container.onboarding


OnboardingServiceDep = Annotated[OnboardingService, Depends(get_onboarding_service)]


def get_search_service(container: ContainerDep) -> SearchService:
    return container.search


SearchServiceDep = Annotated[SearchService, Depends(get_search_service)]


def get_booking_service(container: ContainerDep) -> BookingService:
    return container.booking


BookingServiceDep = Annotated[BookingService, Depends(get_booking_service)]


def get_payment_service(container: ContainerDep) -> PaymentService:
    return container.payment


PaymentServiceDep = Annotated[PaymentService, Depends(get_payment_service)]
