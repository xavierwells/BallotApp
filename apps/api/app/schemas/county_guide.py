"""Allowlisted public facts and separate private publication-control contracts."""

from datetime import date, datetime
from typing import Literal
from urllib.parse import urlsplit
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PublicModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class GuideSource(PublicModel):
    title: str
    publisherName: str
    url: str
    checksum: str = Field(pattern=r"^[a-f0-9]{64}$")
    publishedAt: datetime | None
    retrievedAt: datetime

    @field_validator("url")
    @classmethod
    def direct_source_link(cls, value):
        parsed = urlsplit(value)
        if parsed.scheme not in {"https", "http"} or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("Source needs a direct HTTP(S) publisher link without credentials.")
        return value


class GuideCandidate(PublicModel):
    id: UUID
    ballotLabel: str
    partyLabel: str


class GuideRace(PublicModel):
    id: UUID
    key: str
    ballotTitle: str
    governmentLevel: str
    jurisdictionName: str
    districtLabel: str | None
    seatsAvailable: int
    sourcePage: str
    pdfPageNumber: int | None
    reviewedAt: datetime
    candidates: list[GuideCandidate]


class GuideContent(PublicModel):
    scope: Literal["county_certification_guide"] = "county_certification_guide"
    exactMatch: Literal[False] = False
    completeBallot: Literal[False] = False
    county: str
    electionName: str
    electionDate: date
    raceCount: int
    candidateCount: int
    source: GuideSource
    races: list[GuideRace]


class PublicGuide(GuideContent):
    releaseId: UUID
    publishedAt: datetime


class GuideSummary(PublicModel):
    releaseId: UUID
    publishedAt: datetime
    county: str
    electionName: str
    electionDate: date
    raceCount: int
    candidateCount: int
    exactMatch: Literal[False] = False
    completeBallot: Literal[False] = False


class GuidePage(PublicModel):
    items: list[GuideSummary]
    offset: int
    limit: int
    hasMore: bool


class PublicationBlocker(BaseModel):
    code: str
    message: str


class PublicationStatus(BaseModel):
    batchId: UUID
    canPublish: bool
    contentReady: bool
    blockers: list[PublicationBlocker]
    basisHash: str | None
    currentEventId: int | None
    currentReleaseId: UUID | None
    publishedBatchId: UUID | None
    state: Literal["unpublished", "published", "withdrawn"]


class ManagedRelease(BaseModel):
    batchId: UUID
    releaseId: UUID
    county: str
    publishedAt: datetime


class PublishGuideRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    confirmed: Literal[True] = Field(description="Explicitly release these reviewed official facts with attribution; no source PDF or personal-ballot claim.")
    basisHash: str = Field(pattern=r"^[a-f0-9]{64}$")
    expectedEventId: int | None = Field(ge=1, strict=True, description="Echo currentEventId; null only before the first publication.")


class WithdrawGuideRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    confirmed: Literal[True]
    expectedEventId: int = Field(ge=1, strict=True)
    reason: str = Field(min_length=1, max_length=2000, description="Private audit note, never included in public responses.")
