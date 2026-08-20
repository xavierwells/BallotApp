"""Public contracts for exact, unresolved, and browse ballot discovery.

These models contain result identifiers and public civic evidence only. They
must never acquire an address or precise coordinate field.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


def to_camel(value: str) -> str:
    first, *rest = value.split("_")
    return first + "".join(part.capitalize() for part in rest)


class PublicModel(BaseModel):
    """Use camelCase on the wire while retaining conventional Python names."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class BrowseAreaType(StrEnum):
    ZIP = "zip"
    CITY = "city"
    COUNTY = "county"


class ResolutionStatus(StrEnum):
    RESOLVED = "resolved"
    AMBIGUOUS = "ambiguous"
    SOURCE_CONFLICT = "source_conflict"
    NEEDS_REVIEW = "needs_review"
    NOT_FOUND = "not_found"
    NOT_AVAILABLE = "not_available"


class ResolutionReasonCode(StrEnum):
    LOW_GEOCODE_CONFIDENCE = "low_geocode_confidence"
    NO_BOUNDARY_MATCH = "no_boundary_match"
    NEAR_BOUNDARY = "near_boundary"
    BOUNDARY_SOURCE_CONFLICT = "boundary_source_conflict"
    BALLOT_STYLE_CONFLICT = "ballot_style_conflict"
    BALLOT_DATA_UNAVAILABLE = "ballot_data_unavailable"


class SourceCitation(PublicModel):
    authority_name: str = Field(min_length=1, max_length=255)
    source_url: HttpUrl
    checked_at: datetime
    source_label: str = Field(min_length=1, max_length=500)


class GeographicSupport(PublicModel):
    geographic_area_id: UUID
    area_type: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=255)
    boundary_version_id: UUID
    explanation: str = Field(min_length=1, max_length=1000)
    source: SourceCitation


class BallotChoice(PublicModel):
    ballot_version_id: UUID
    label: str = Field(min_length=1, max_length=500)
    election_name: str = Field(min_length=1, max_length=500)
    election_date: date = Field(description="Election date, serialized in YYYY-MM-DD form.")
    official_source: SourceCitation


class PlausibleBallot(PublicModel):
    ballot: BallotChoice
    supported_by: list[GeographicSupport] = Field(min_length=1)
    explanation: str = Field(min_length=1, max_length=2000)


class ResolutionBase(PublicModel):
    address_persisted: Literal[False] = False
    demonstration: bool = False
    reason_codes: list[ResolutionReasonCode] = Field(default_factory=list)


class ResolvedBallotResponse(ResolutionBase):
    status: Literal[ResolutionStatus.RESOLVED] = ResolutionStatus.RESOLVED
    confidence: int = Field(ge=0, le=100)
    ballot: BallotChoice
    supported_by: list[GeographicSupport] = Field(min_length=1)


class MultipleBallotsResponse(ResolutionBase):
    status: Literal[
        ResolutionStatus.AMBIGUOUS,
        ResolutionStatus.SOURCE_CONFLICT,
    ]
    confidence: int = Field(ge=0, le=100)
    message: str = Field(min_length=1, max_length=2000)
    plausible_ballots: list[PlausibleBallot] = Field(min_length=2)

    @model_validator(mode="after")
    def ballot_versions_are_unique(self) -> "MultipleBallotsResponse":
        identifiers = [item.ballot.ballot_version_id for item in self.plausible_ballots]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("plausible ballots must use unique ballot version IDs")
        return self


class NeedsReviewResponse(ResolutionBase):
    status: Literal[ResolutionStatus.NEEDS_REVIEW] = ResolutionStatus.NEEDS_REVIEW
    confidence: int = Field(ge=0, le=100)
    message: str = Field(min_length=1, max_length=2000)
    plausible_ballots: list[PlausibleBallot] = Field(default_factory=list)
    official_contact_links: list[HttpUrl] = Field(default_factory=list)


class NotFoundResponse(ResolutionBase):
    status: Literal[ResolutionStatus.NOT_FOUND] = ResolutionStatus.NOT_FOUND
    message: str = Field(min_length=1, max_length=2000)
    official_contact_links: list[HttpUrl] = Field(default_factory=list)


class NotAvailableResponse(ResolutionBase):
    status: Literal[ResolutionStatus.NOT_AVAILABLE] = ResolutionStatus.NOT_AVAILABLE
    message: str = Field(min_length=1, max_length=2000)


BallotResolutionResponse = Annotated[
    ResolvedBallotResponse
    | MultipleBallotsResponse
    | NeedsReviewResponse
    | NotFoundResponse
    | NotAvailableResponse,
    Field(discriminator="status"),
]


class BrowseBallotMatch(PublicModel):
    ballot: BallotChoice
    geographic_support: list[GeographicSupport] = Field(min_length=1)
    relationship: Literal["within", "overlaps"]
    explanation: str = Field(min_length=1, max_length=2000)


class BallotBrowseResponse(PublicModel):
    status: Literal["available", "not_found", "not_available"]
    area_type: BrowseAreaType
    query: str = Field(min_length=1, max_length=255)
    exact_match: Literal[False] = False
    message: str = Field(min_length=1, max_length=2000)
    matches: list[BrowseBallotMatch] = Field(default_factory=list)

    @model_validator(mode="after")
    def available_requires_matches(self) -> "BallotBrowseResponse":
        if self.status == "available" and not self.matches:
            raise ValueError("available browse responses require at least one ballot")
        if self.status != "available" and self.matches:
            raise ValueError("only available browse responses may contain ballots")
        return self
