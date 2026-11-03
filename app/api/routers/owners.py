from fastapi import APIRouter, status

from app.api.dependencies import OnboardingServiceDep
from app.api.schemas.property import OwnerCreate, OwnerOut, PropertyCreate, PropertyOut

router = APIRouter(prefix="/owners", tags=["onboarding"])


@router.post("", status_code=status.HTTP_201_CREATED)
def register_owner(body: OwnerCreate, service: OnboardingServiceDep) -> OwnerOut:
    """Register an owner account: a standalone hotelier or a multi-property chain."""
    return OwnerOut.from_domain(service.register_owner(body.name, body.account_type))


@router.get("/{owner_id}")
def get_owner(owner_id: str, service: OnboardingServiceDep) -> OwnerOut:
    return OwnerOut.from_domain(service.get_owner(owner_id))


@router.post("/{owner_id}/properties", status_code=status.HTTP_201_CREATED)
def onboard_property(
    owner_id: str, body: PropertyCreate, service: OnboardingServiceDep
) -> PropertyOut:
    """Onboard a property, with its room types and pricing, under an owner."""
    return PropertyOut.from_domain(service.onboard_property(owner_id, body.to_details()))


@router.get("/{owner_id}/properties")
def list_owner_properties(owner_id: str, service: OnboardingServiceDep) -> list[PropertyOut]:
    return [PropertyOut.from_domain(p) for p in service.list_properties(owner_id)]
