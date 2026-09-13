# Private certification guide preview

## What is ready

Staff can browse imported county certification records at
[`/editorial/preview`](http://localhost:3000/editorial/preview), linked from the
editorial workspace and imported-county overview. This is a real-data preview,
not the synthetic address-resolution demo. It uses the existing staff session.

Choose a county, then search its offices, candidate names, districts or parties.
Matching races keep their complete candidate roster and certification order;
search never picks a candidate, changes review, or implies official ballot order.
Each race links to the retained source page and offers historical review details.
The document panel includes its publisher link and SHA-256 checksum. Known PDF
cover offsets use the same checksum-specific navigation as the review workspace.

The operator reported completion of county review/import on 2026-09-12. The
database's saved decisions and import receipts remain the evidence of exactly
what was accepted and imported; this document does not create approvals.

The operator accepted the real-data preview visually on 2026-09-12. The next
slice adds separate [county-guide publication controls](COUNTY_GUIDE_PUBLICATION.md)
and public guide pages. Viewing this private preview still never publishes data.

## Run it

The commands below describe the original preview-only slice. **Current code also
includes publication migration 019**: use the test/backup/upgrade steps in
[`COUNTY_GUIDE_PUBLICATION.md`](COUNTY_GUIDE_PUBLICATION.md) before running that update.

The existing stack must already have completed migration `018_shared_race_reviews`.
The original preview-only slice added **no migration, dependency, service, environment variable, or new
development-container setup**. Do not repeat review, download or setup.

Run the isolated database checks, then rebuild only the API and production web:

```powershell
docker compose --profile tests run --build --rm api-test
docker compose -f compose.yaml up -d --build --no-deps api web
```

Sign in at `/editorial`, then choose **Private guide preview**.
If no counties appear, confirm their status is **Imported · unpublished** in the
review workspace. Accepted draft sections alone are not an import. If a newer
draft exists, finish its controlled review/import process rather than treating
the older import as current. Conflicting canonical corrections still require
operator reconciliation; this preview never overwrites records.

## Scope and limitations

- The preview reader remains staff-only and read-only. Publication controls are
  separate explicit operations. The static page shell holds
  no civic records; authenticated API responses supply all private content.
- Certification names, offices and parties are not a complete or personalized
  ballot. City/school races, propositions, official ballot styles, geographic
  applicability, biographies, statements and voting logistics remain separate.
- Counts are county-scoped entries, not unique people across counties.
- Review evidence is the historical import snapshot, not a fresh source check or
  current reviewer-eligibility assessment. Local acceptances and shared content
  reviews are labeled separately from county-source confirmation. Legacy imports
  without a snapshot show unavailable review details, never invented reviewers.
- Reading this route does not publish or create anything. The separate release
  workflow publishes only an allowlisted copy after publisher confirmation; no
  resolver fallback is connected to the preview.
- No address entry, coordinates, browser storage or analytics are introduced.
  Search is in memory. Sign-out, unauthorized responses and failed county loads
  clear the displayed records; abandoned requests cannot replace a later county.

## API contract

Both endpoints use the existing editorial session cookie, publication scoping,
origin policy and `Cache-Control: no-store, private`. OpenAPI, Swagger and ReDoc
document response schemas and errors automatically.

| Read endpoint | Response |
| --- | --- |
| `GET /api/v1/editorial/guide-preview` | Up to 100 current imported county summaries, newest election first. A newer draft excludes the older import. Empty list if none qualify. |
| `GET /api/v1/editorial/guide-preview/{batch_id}` | Canonical records, source metadata, and saved import-review context. An explicitly requested historical import is marked `current: false`. |

Responses distinguish `401` (sign-in required), `403` (untrusted browser origin),
`404` (not imported, missing, or inaccessible), `409` (record/citation/receipt
conflict), `422` (invalid identifier), and `503` (editorial storage unavailable).
Draft and cross-publication identifiers intentionally have the same 404 response.

The reader uses the immutable import manifest to select the corresponding
election, race keys and source document. Display labels and IDs come from
`elections`, `races`, `offices`, and `candidates`, joined through scoped election
and candidacy citations. Every expected candidate and page citation must match.
Missing or changed records stop the preview with a 409; extraction text is never
used as a fallback. The saved promotion snapshot supplies historical review data.

## Verification

Local checks after the boundary-scope fix on 2026-09-12: **166 API tests passed, 14 database tests skipped,
1 existing Starlette/httpx warning**; **27 frontend tests passed**; production web
build passed. Node also reports the existing module-type warning in frontend
unit tests. Mocked browser checks passed for staff-only access, county selection,
whole-roster search, citations, shared-review labels, responsive desktop/mobile
layouts, empty/conflict states, session expiry, stale-request cancellation and
sign-out. No reading/filtering operation submitted a review or publication.

The PostgreSQL integration test covers real canonical joins, promotion gating,
source citations, session protection, superseding drafts and canonical drift.
The operator's Docker run returned **176 passed, 1 failed, 16 warnings**: the
preview/editorial tests passed, but the older migration test read another test
publication's boundary. Its unscoped spatial query and first-result assumption
were exposed by retained fixtures in the running test database.

Boundary reads now require the configured publication UUID, and both the subject
and publisher must belong to that publication. The migration regression keeps
identical boundaries in two publications and asserts exact, isolated membership
sets, plus no results for an unrelated publication. Local tests check query
binding and production pipeline wiring. No migration or data deletion is needed.

For future changes, re-run the isolated Docker suite above after rebuilding,
including a repeat against retained `test-postgres` fixtures. Local mocks do not
replace database checks. The operator subsequently reported green checks and
accepted both the preview and publication slice on 2026-09-12; no new exact count
was supplied.

The [explicit publication handoff](COUNTY_GUIDE_PUBLICATION.md) and public
county-guide pages are accepted. The current [navigation slice](BROWSING_AND_STAFF_NAVIGATION.md)
adds homepage staff login, a site map and area-to-guide links. Complete ballots and exact address
matching still depend on authoritative ballot styles and geographic evidence.
