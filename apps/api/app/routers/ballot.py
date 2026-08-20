import re

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.ballot_browsing import BallotBrowser, browser_from_environment

from app.schemas.ballot_resolution import (
    BallotBrowseResponse,
    BallotResolutionResponse,
    BrowseAreaType,
)
from app.resolution_pipeline import (
    ResolutionPipeline,
    SyntheticDemoResolutionPipeline,
    pipeline_from_environment,
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


class LocationResolutionRequest(BaseModel):
    """Request-only browser location. Coordinates must never be persisted or logged."""

    longitude: float = Field(ge=-180, le=180)
    latitude: float = Field(ge=-90, le=90)
    accuracy_meters: float = Field(alias="accuracyMeters", ge=0, le=10_000)


@router.post(
    "/resolve",
    summary="Resolve an address without retaining it",
    description=(
        "Runs the configured request-scoped geocoder, verified-boundary resolver, "
        "and combination ballot matcher. It fails closed as `not_available` until "
        "an approved provider and reviewed election context are configured."
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
def resolve_preview(
    request: AddressResolutionRequest,
    pipeline: ResolutionPipeline | SyntheticDemoResolutionPipeline = Depends(pipeline_from_environment),
) -> BallotResolutionResponse:
    """Resolve an address in request memory and discard it before returning."""
    return pipeline.resolve(request.address)


@router.post(
    "/resolve-location",
    summary="Resolve a current location without retaining it",
    description=(
        "Accepts a browser-provided coordinate and accuracy radius for this request only. "
        "The values are not stored or returned, and uncertain boundary matches fail closed."
    ),
    response_model=BallotResolutionResponse,
    response_model_by_alias=True,
)
def resolve_location(
    request: LocationResolutionRequest,
    pipeline: ResolutionPipeline | SyntheticDemoResolutionPipeline = Depends(pipeline_from_environment),
) -> BallotResolutionResponse:
    return pipeline.resolve_location(
        longitude=request.longitude,
        latitude=request.latitude,
        accuracy_meters=request.accuracy_meters,
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
    query: str = Query(min_length=1, max_length=255, pattern=r".*\S.*"),
    browser: BallotBrowser = Depends(browser_from_environment),
) -> BallotBrowseResponse:
    """Browse a coarse area without accepting or inferring a voter address."""
    normalized_query = query.strip()
    if area_type is BrowseAreaType.ZIP and not re.fullmatch(r"\d{5}(?:-\d{4})?", normalized_query):
        raise HTTPException(status_code=422, detail="ZIP code must use 12345 or 12345-6789 format")
    return browser.browse(area_type, normalized_query)
