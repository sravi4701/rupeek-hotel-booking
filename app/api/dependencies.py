from typing import Annotated, cast

from fastapi import Depends, Request

from app.api.container import Container
from app.application.onboarding_service import OnboardingService


def get_container(request: Request) -> Container:
    return cast(Container, request.app.state.container)


ContainerDep = Annotated[Container, Depends(get_container)]


def get_onboarding_service(container: ContainerDep) -> OnboardingService:
    return container.onboarding


OnboardingServiceDep = Annotated[OnboardingService, Depends(get_onboarding_service)]
