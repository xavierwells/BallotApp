from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from app.schemas.ballot_resolution import (
    BallotBrowseResponse,
    BallotResolutionResponse,
    BrowseAreaType,
    NotAvailableResponse,
)

router = APIRouter(prefix="/ballots", tags=["ballots"])


class AddressResolutionRequest(BaseModel):
    """Request-only address input. It must never be persisted or logged."""

    address: str = Field(
        min_length=5,
        max_length=300,
        description="Used only for this request and discarded before the response is returned.",
        examples=["914 Example Street, Copperas Cove, TX 76522"],
    )


@router.post(
    "/resolve",
    summary="Resolve an address without retaining it",
    description=(
        "Contract-first endpoint. Until the approved geocoder and authoritative "
        "boundary matcher are connected, it returns `not_available`. The final "
        "contract supports exact, ambiguous, source-conflict, needs-review, and "
        "not-found results."
    ),
    response_model=BallotResolutionResponse,
    response_model_by_alias=True,
)
@router.post(
    "/resolve-preview",
    summary="Deprecated preview alias for address resolution",
    response_model=BallotResolutionResponse,
    response_model_by_alias=True,
    deprecated=True,
)
def resolve_preview(request: AddressResolutionRequest) -> BallotResolutionResponse:
    """Accept an address ephemerally; no geocoder or storage is connected yet."""
    del request
    return NotAvailableResponse(
        status="not_available",
        message="Ballot resolution is not connected yet. The submitted address was discarded.",
    )


@router.get(
    "/browse",
    summary="Browse ballots without entering an address",
    description=(
        "Lists ballots associated with a user-selected ZIP code, city, or county. "
        "Browse results are coarse area matches and never claim to be the voter's exact ballot."
    ),
    response_model=BallotBrowseResponse,
    response_model_by_alias=True,
)
def browse_ballots(
    area_type: BrowseAreaType = Query(alias="areaType"),
    query: str = Query(min_length=1, max_length=255),
) -> BallotBrowseResponse:
    """Expose the browse contract without pretending ballot data is connected."""
    return BallotBrowseResponse(
        status="not_available",
        area_type=area_type,
        query=query,
        message="Ballot browsing is not connected yet. No exact voter match was attempted.",
    )
