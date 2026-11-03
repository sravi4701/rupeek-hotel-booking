from fastapi import APIRouter

from app.api.dependencies import OnboardingServiceDep
from app.api.schemas.property import PropertyOut

router = APIRouter(prefix="/properties", tags=["properties"])


@router.get("/{property_id}")
def get_property(property_id: str, service: OnboardingServiceDep) -> PropertyOut:
    return PropertyOut.from_domain(service.get_property(property_id))
