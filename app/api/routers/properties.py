from typing import Annotated

from fastapi import APIRouter, Query

from app.api.dependencies import OnboardingServiceDep, SearchServiceDep
from app.api.schemas.property import PropertyOut
from app.api.schemas.search import SearchQuery, SearchResultOut

router = APIRouter(prefix="/properties", tags=["properties"])


# Must be declared before "/{property_id}" so "search" isn't read as an id.
@router.get("/search")
def search_properties(
    query: Annotated[SearchQuery, Query()], service: SearchServiceDep
) -> list[SearchResultOut]:
    """Properties with at least one room type available for the whole stay, cheapest first."""
    results = service.search(query.to_criteria(), query.to_filters())
    return [SearchResultOut.from_domain(r) for r in results]


@router.get("/{property_id}")
def get_property(property_id: str, service: OnboardingServiceDep) -> PropertyOut:
    return PropertyOut.from_domain(service.get_property(property_id))
