from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/ballots", tags=["ballots"])


class BallotResolutionPreview(BaseModel):
    """Non-persistent result returned while the authoritative resolver is built."""

    status: str = Field(examples=["not_available"])
    message: str
    addressPersisted: bool = False


class AddressResolutionRequest(BaseModel):
    """Request-only address input. It must never be persisted or logged."""

    address: str = Field(
        min_length=5,
        max_length=300,
        description="Used only for this request and discarded before the response is returned.",
        examples=["914 Example Street, Copperas Cove, TX 76522"],
    )


@router.post(
    "/resolve-preview",
    summary="Preview ballot resolution without retaining an address",
    response_model=BallotResolutionPreview,
)
def resolve_preview(request: AddressResolutionRequest) -> BallotResolutionPreview:
    """Accept an address ephemerally; no geocoder or storage is connected yet."""
    del request
    return BallotResolutionPreview(
        status="not_available",
        message="Ballot resolution is not connected yet. The submitted address was discarded.",
    )
