"""Read-only, staff-only certification preview contracts (not public ballots)."""

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class PreviewSummary(BaseModel):
    batchId: UUID
    county: str
    revision: int
    electionName: str
    electionDate: date
    raceCount: int
    candidateCount: int = Field(description="County-scoped candidate entries, not distinct people across counties.")
    importedAt: datetime


class PreviewSource(BaseModel):
    title: str
    url: str
    checksum: str


class PreviewAcceptance(BaseModel):
    kind: Literal["local", "shared"]
    reviewer: str
    at: datetime
    decisionId: str
    county: str
    batchId: UUID
    sourcePage: str
    pdfPageNumber: int | None


class PreviewCandidate(BaseModel):
    id: UUID
    ballotLabel: str
    partyLabel: str


class PreviewRace(BaseModel):
    id: UUID
    key: str
    ballotTitle: str
    governmentLevel: str
    jurisdictionName: str
    districtLabel: str | None
    seatsAvailable: int
    sourcePage: str
    pdfPageNumber: int | None
    candidates: list[PreviewCandidate]
    reviewStatusAtImport: Literal["reviewed", "unavailable"]
    recordedAcceptances: list[PreviewAcceptance] = Field(
        description="Historical local acceptances and shared evidence saved in the import receipt; not new approvals or a live reviewer eligibility check.")


class GuidePreview(PreviewSummary):
    scope: Literal["private_certification_preview"] = "private_certification_preview"
    exactMatch: Literal[False] = False
    publicationAllowed: Literal[False] = False
    current: bool
    importedBy: str
    countySourceConfirmedBy: str | None
    reviewReceiptAvailable: bool
    source: PreviewSource
    races: list[PreviewRace]
