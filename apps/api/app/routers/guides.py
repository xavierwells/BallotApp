"""Public, read-only county certification guides; not exact-ballot results."""

from uuid import UUID
from fastapi import APIRouter, Query
from app.county_guides import list_public_guides, read_public_guide
from app.database import get_engine
from app.schemas.county_guide import GuidePage, PublicGuide

router = APIRouter(prefix="/guides", tags=["county guides"])
ERRORS = {503: {"description": "Guide storage unavailable."}}


@router.get("", response_model=GuidePage, responses=ERRORS,
            summary="List explicitly published county guides without an address",
            description="Public, no-store, offset pagination within the configured pilot publication. "
                        "Only current published releases with active source approval are returned. "
                        "Optional county filters the full county label (case-insensitive, outer whitespace ignored); "
                        "this is directory navigation, never address, ZIP, city or ballot applicability. "
                        "Empty is not proof that a county has no election. No private drafts or reviewer identities.")
def guides(offset: int = Query(default=0, ge=0, le=10000), limit: int = Query(default=20, ge=1, le=50),
           county: str | None = Query(default=None, min_length=1, max_length=255,
                                    description="Full county label, e.g. Coryell County. No fuzzy or partial matching.")):
    with get_engine().connect() as connection:
        return list_public_guides(connection, offset=offset, limit=limit, county=county)


@router.get("/{release_id}", response_model=PublicGuide,
            responses={**ERRORS, 404: {"description": "Missing, unpublished, withdrawn, superseded or inaccessible guide."}},
            summary="Read the frozen, attributed facts in a published county certification guide",
            description="Not a complete or personal ballot. Sources are direct publisher links, not retained PDF downloads. "
                        "Source and content-review dates are historical, not a fresh source check. "
                        "New drafts leave this release unchanged until explicit replacement/withdrawal; source revocation hides it.")
def guide(release_id: UUID):
    with get_engine().connect() as connection:
        return read_public_guide(connection, release_id)
