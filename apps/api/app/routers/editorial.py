"""Private editorial API. Authentication applies to drafts and retained PDFs."""

import os
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import text

from app.database import get_engine
from app.document_storage import DocumentStorageError, document_store_from_environment
from app.editorial_auth import COOKIE, login, require_editor, require_origin, token_hash
from app.editorial_review import batch_detail, batch_row, promote, record_decision, submit_sections
from app.editorial_preview import guide_preview, list_previews
from app.schemas.editorial_preview import GuidePreview, PreviewSummary
from app.county_guides import publication_status, publish_guide, withdraw_guide, managed_releases
from app.schemas.county_guide import PublicationStatus, PublishGuideRequest, WithdrawGuideRequest, ManagedRelease

router = APIRouter(prefix="/editorial", tags=["editorial"])
AUTH_ERRORS = {401: {"description": "Staff sign-in required."}, 404: {"description": "No accessible batch."}}
WRITE_ERRORS = {**AUTH_ERRORS, 403: {"description": "Invalid browser origin."},
                409: {"description": "Superseded draft, unresolved review or conflicting import."}}
PREVIEW_ERRORS = {**AUTH_ERRORS, 403: {"description": "Untrusted browser origin."},
                  503: {"description": "Editorial storage is unavailable."}}


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=1, max_length=256)


class Staff(BaseModel):
    id: UUID
    username: str
    publicationId: UUID
    canPublish: bool = False


class ReviewRequest(BaseModel):
    raceKeys: list[str] = Field(min_length=1, max_length=200)
    decision: Literal["accepted", "flagged"]
    note: str = Field(default="", max_length=2000)


class FieldCorrection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    field: Literal["ballotTitle", "ballotLabel", "partyLabel"]
    candidateIndex: int | None = Field(default=None, ge=0, strict=True,
        description="Zero-based candidate position within this immutable section; absent for office title.")
    value: str = Field(min_length=1, max_length=255)


class SectionDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    raceKey: str = Field(min_length=1, max_length=255)
    decision: Literal["accepted", "flagged"]
    note: str = Field(default="", max_length=2000)
    corrections: list[FieldCorrection] = Field(default_factory=list, max_length=100)


class SectionReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sections: list[SectionDecision] = Field(min_length=1, max_length=200)
    confirmed: Literal[True] = Field(description="Reviewer confirms acceptances and proposed corrections were compared with the cited source.")


class ImportReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    confirmedCountyCoverage: bool = Field(default=False, strict=True,
        description="Human checked that this county's listed contests appear on its cited pages; not voter/precinct applicability.")
    reviewBasisHash: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$",
        description="Echo the batch's current evidence hash to reject changed/stale shared reviews.")


class Source(BaseModel):
    title: str
    url: str
    checksum: str


class Election(BaseModel):
    name: str
    authorityName: str
    date: str
    type: str


class Candidate(BaseModel):
    ballotLabel: str
    partyLabel: str


class Decision(BaseModel):
    decisionId: str
    originalDecisionId: str
    reviewer: str
    decision: str
    note: str
    at: str
    carriedForward: bool = False


class SharedReview(BaseModel):
    decisionId: str
    originalDecisionId: str
    reviewer: str
    at: str
    county: str
    batchId: UUID
    raceKey: str
    sourcePage: str
    pdfPageNumber: int | None


class CorrectedField(BaseModel):
    field: str
    candidateIndex: int | None
    before: str
    after: str


class CorrectionEvent(BaseModel):
    reviewer: str
    at: str
    note: str
    changes: list[CorrectedField]


class Race(BaseModel):
    key: str
    ballotTitle: str
    governmentLevel: str
    jurisdictionName: str
    districtLabel: str | None = None
    sourcePage: str
    pdfPageNumber: int | None = Field(default=None, ge=1,
        description="One-based physical PDF page for viewer navigation. sourcePage remains the printed citation; "
                    "known document layouts are keyed by checksum. Null means navigate manually.")
    seatsAvailable: int = 1
    candidates: list[Candidate]
    reviewStatus: Literal["unreviewed", "reviewed", "flagged"]
    approvalCount: int
    localApprovalCount: int
    countySourceReviewed: bool
    sharedReviews: list[SharedReview]
    matchingCounties: list[str]
    sharedReviewBlockedReason: str | None
    decisions: list[Decision]
    corrections: list[CorrectionEvent] = Field(default_factory=list)


class BatchSummary(BaseModel):
    id: UUID
    county: str
    revision: int
    contentHash: str
    election: Election
    requiredReviewers: int
    current: bool
    imported: bool
    reviewedRaces: int
    raceCount: int
    candidateCount: int
    source: Source
    sharedReviewedRaces: int
    requiresCountyConfirmation: bool
    reviewBasisHash: str
    countySourceConfirmedBy: str | None


class Batch(BatchSummary):
    races: list[Race]


@router.post("/login", response_model=dict[str, str], dependencies=[Depends(require_origin)],
             responses={401: {"description": "Incorrect credentials or temporarily locked account."},
                        403: {"description": "Invalid browser origin."}},
             summary="Sign in with a provisioned staff account")
def sign_in(payload: LoginRequest, response: Response):
    token = login(payload.username, payload.password)
    if token is None:
        raise HTTPException(401, "Could not sign in. Check your details or wait five minutes after repeated failures.")
    response.set_cookie(COOKIE, token, max_age=8 * 60 * 60, httponly=True, samesite="strict",
                        secure=os.getenv("APP_ENV", "development") != "development", path="/api/v1/editorial")
    return {"status": "signed_in"}


@router.get("/me", response_model=Staff, responses=AUTH_ERRORS, summary="Read the signed-in staff identity")
def me(user: dict = Depends(require_editor)):
    return {"id": user["id"], "username": user["username"], "publicationId": user["publication_id"],
            "canPublish": user.get("can_publish", False)}


@router.post("/logout", response_model=dict[str, str], dependencies=[Depends(require_origin)],
             summary="Revoke this editorial session")
def sign_out(request: Request, response: Response):
    token = request.cookies.get(COOKIE)
    if token:
        with get_engine().begin() as connection:
            connection.execute(text("DELETE FROM editorial_sessions WHERE token_hash=:t"), {"t": token_hash(token)})
    response.delete_cookie(COOKIE, path="/api/v1/editorial")
    return {"status": "signed_out"}


@router.get("/batches", response_model=list[BatchSummary], responses=AUTH_ERRORS,
            summary="List current private review batches for this staff publication")
def batches(user: dict = Depends(require_editor)):
    with get_engine().connect() as connection:
        ids = connection.execute(text(
            "SELECT DISTINCT ON (batch_key) id FROM editorial_batches WHERE publication_id=:p "
            "ORDER BY batch_key,version DESC LIMIT 100"
        ), {"p": user["publication_id"]}).scalars().all()
        return [batch_detail(connection, user["publication_id"], batch_id) for batch_id in ids]


@router.get("/guide-preview", response_model=list[PreviewSummary], responses=PREVIEW_ERRORS,
            summary="List current imported county certifications for private guide preview",
            description="Staff-only, no-store. Returns up to 100 current imported revisions in this publication, "
                        "newest election first. Drafts and imports with a newer draft are excluded. Counts are "
                        "certification entries, not ballot coverage or distinct people across counties.")
def previews(user: dict = Depends(require_editor)):
    with get_engine().connect() as connection:
        return list_previews(connection, user["publication_id"])


@router.get("/guide-preview/{batch_id}", response_model=GuidePreview,
            responses={**PREVIEW_ERRORS, 409: {"description": "Canonical records or citations differ from the import receipt."}},
            summary="Preview canonical certification facts and historical import review evidence",
            description="Read-only and staff-only. Names/parties/offices come from canonical civic records and must "
                        "match the imported certification and citations. Never falls back to draft data. "
                        "Older imported revisions are explicitly marked current=false. Legacy imports without "
                        "a review snapshot show unavailable review details; no decisions are invented. "
                        "This is not a complete or personalized ballot, and does not authorize publication.")
def preview(batch_id: UUID, user: dict = Depends(require_editor)):
    with get_engine().connect() as connection:
        return guide_preview(connection, user["publication_id"], batch_id)


@router.get("/guide-preview/{batch_id}/publication", response_model=PublicationStatus,
            responses=PREVIEW_ERRORS, summary="Check county-guide release readiness and current publication state",
            description="Read-only, staff-only. Rechecks existing reviews, source approval and canonical citations. "
                        "Does not renew a verification. Publisher permission is separate from content readiness.")
def guide_publication_status(batch_id: UUID, user: dict = Depends(require_editor)):
    with get_engine().connect() as connection:
        return publication_status(connection, user, batch_id)


@router.get("/guide-releases", response_model=list[ManagedRelease], responses=PREVIEW_ERRORS,
            summary="Find recorded public releases even when their current preview is unavailable",
            description="Staff-only, up to 100 releases. New drafts or source/canonical conflicts never remove "
                        "the publisher's withdrawal entry point. Public source-approval checks remain separate.")
def current_guide_releases(user: dict = Depends(require_editor)):
    with get_engine().connect() as connection:
        return managed_releases(connection, user["publication_id"])


@router.post("/guide-preview/{batch_id}/publish", response_model=dict[str, str],
             dependencies=[Depends(require_origin)], responses={**WRITE_ERRORS, 503: {"description": "Storage unavailable."}},
             summary="Explicitly publish or replace a reviewed county certification guide",
             description="Publisher capability required. Rechecks current evidence and an optimistic state token, "
                         "then atomically records an immutable allowlisted release and publish event. "
                         "No PDF, staff data, ballot style or exact voter match is published. New drafts never auto-replace it.")
def publish_county_guide(batch_id: UUID, payload: PublishGuideRequest, user: dict = Depends(require_editor)):
    with get_engine().begin() as connection:
        return publish_guide(connection, user, batch_id, payload.basisHash, payload.expectedEventId)


@router.post("/guide-releases/{release_id}/withdraw", response_model=dict[str, str],
             dependencies=[Depends(require_origin)], responses=WRITE_ERRORS,
             summary="Take the current county guide offline while preserving its private audit history",
             description="Publisher capability required. Rejects stale release/event IDs; never deletes a release. "
                         "The reason is private. Public readers return 404 after the withdrawal commits.")
def withdraw_county_guide(release_id: UUID, payload: WithdrawGuideRequest, user: dict = Depends(require_editor)):
    with get_engine().begin() as connection:
        return withdraw_guide(connection, user, release_id, payload.expectedEventId, payload.reason)


@router.get("/batches/{batch_id}", response_model=Batch, responses=AUTH_ERRORS,
            summary="Compare extracted official facts and saved review decisions")
def detail(batch_id: UUID, user: dict = Depends(require_editor)):
    with get_engine().connect() as connection:
        return batch_detail(connection, user["publication_id"], batch_id)


@router.get("/batches/{batch_id}/source", responses={**AUTH_ERRORS, 200: {"content": {"application/pdf": {}}},
            503: {"description": "Private source missing or failed integrity verification."}}, response_class=Response,
            summary="View the checksum-verified private source PDF")
def source(batch_id: UUID, user: dict = Depends(require_editor)):
    with get_engine().connect() as connection:
        batch = batch_row(connection, user["publication_id"], batch_id)
    try:
        content = document_store_from_environment().read_bytes(batch["storage_key"])
    except (DocumentStorageError, OSError, TypeError) as error:
        raise HTTPException(503, "The retained source could not be opened. Ask the operator to check document storage.") from error
    return Response(content, media_type="application/pdf", headers={
        "Content-Disposition": 'inline; filename="official-source.pdf"',
        "X-Content-Type-Options": "nosniff",
        "Content-Security-Policy": "frame-ancestors 'self' " + os.getenv("PUBLIC_WEB_ORIGIN", "http://localhost:3000"),
    })


@router.post("/batches/{batch_id}/decisions", response_model=Batch, responses=WRITE_ERRORS,
             dependencies=[Depends(require_origin)], summary="Accept or flag an explicit set of races",
             description="One staff review suffices for official transcription. Decisions are append-only and scoped "
                         "to this immutable draft revision. Flags require a note. No publication occurs.")
def decide(batch_id: UUID, payload: ReviewRequest, user: dict = Depends(require_editor)):
    with get_engine().begin() as connection:
        return record_decision(connection, user, batch_id, payload.raceKeys, payload.decision, payload.note)


@router.post("/batches/{batch_id}/review", response_model=Batch, responses=WRITE_ERRORS,
             dependencies=[Depends(require_origin)], summary="Submit section decisions and field corrections together",
             description="Atomically save mixed Accept/Flag decisions with section-specific notes. "
                         "Corrections create an immutable draft revision, retain original values and require later "
                         "acceptance of changed sections. Unchanged section reviews carry forward explicitly. "
                         "The returned batch id may change. No publication or canonical record change occurs.")
def submit_review(batch_id: UUID, payload: SectionReviewRequest, user: dict = Depends(require_editor)):
    with get_engine().begin() as connection:
        return submit_sections(connection, user, batch_id, [section.model_dump() for section in payload.sections])


@router.post("/batches/{batch_id}/import", response_model=Batch, responses=WRITE_ERRORS,
             dependencies=[Depends(require_origin)], summary="Import the reviewed county as unpublished civic records",
             description="All race content must meet the human review policy. Shared reviews require a separate county-source "
                         "confirmation and the current reviewBasisHash. No body is needed for fully local reviews. "
                         "The atomic import retains its exact review evidence; it creates no public ballot or voter applicability claim.")
def import_reviewed(batch_id: UUID, payload: ImportReviewRequest | None = None, user: dict = Depends(require_editor)):
    with get_engine().begin() as connection:
        return promote(connection, user, batch_id,
                       confirmed_county_coverage=payload.confirmedCountyCoverage if payload else False,
                       expected_basis=payload.reviewBasisHash if payload else None)
