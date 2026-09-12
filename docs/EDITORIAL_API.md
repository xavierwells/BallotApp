# Staff review API

The first staff API is versioned under `/api/v1/editorial`. Swagger at `/docs`
and OpenAPI at `/openapi.json` include its cookie authentication and typed
request/response models. See [the workflow](EDITORIAL_VERIFICATION_WORKFLOW.md)
for local setup and browser operation.

## Access and privacy

Provisioned staff accounts belong to one publication; no public registration.
Login sets an HttpOnly, SameSite=Strict cookie, Secure outside development.
The browser sends credentials; all mutations require an `Origin` exactly equal
to `PUBLIC_WEB_ORIGIN`. Requests carrying another origin are rejected, including
reads. Server-side tooling can read with an authenticated cookie and no Origin,
but must supply the configured Origin for writes. Do not log passwords or cookies.

All responses use `Cache-Control: no-store`; inaccessible cross-publication
batches/documents return 404. Account/session storage contains no voter data.
Eight-hour sessions are stored as hashes. Logout, password reset, account disable,
and a new successful login revoke the affected session. Only one active session
per account is supported initially. Five bad passwords lock the account for
five minutes; production ingress should also rate-limit login requests.

## Endpoints

| Method and path | Purpose |
| --- | --- |
| `POST /login` | `{ "username": "xavier", "password": "..." }`; sets session cookie, never returns its raw token in JSON. |
| `GET /me` | Current staff identity and publication. |
| `POST /logout` | Revoke the current session and expire its cookie. |
| `GET /batches` | Up to 100 current county revisions in this publication, with progress. |
| `GET /batches/{id}` | Source metadata, immutable revision, races/candidate labels, latest decisions and field correction history. |
| `GET /batches/{id}/source` | Authenticated retained PDF, checksum-checked on read; no public storage URL. |
| `POST /batches/{id}/review` | Atomically save mixed section decisions and optional transcription corrections; returns the current batch, possibly with a new ID. |
| `POST /batches/{id}/decisions` | Compatibility endpoint: one shared decision/note for specified race keys; the server supplies staff identity and time. |
| `POST /batches/{id}/import` | Import reviewed content into private records, with explicit county coverage confirmation when using shared reviews. |

## Section review and correction

The browser uses `/batches/{id}/review`. Example body (keys come from the batch):

```json
{
  "confirmed": true,
  "sections": [
    { "raceKey": "office-one", "decision": "accepted" },
    {
      "raceKey": "office-two",
      "decision": "flagged",
      "note": "Name was transcribed incorrectly; corrected to match the PDF.",
      "corrections": [
        { "field": "ballotLabel", "candidateIndex": 0, "value": "Example Candidate" }
      ]
    }
  ]
}
```

`confirmed: true` explicitly confirms comparison against the source. There must
be 1–200 distinct, known section keys. Each section has its own decision, note
(up to 2,000 characters), and optional corrections. A flag requires a nonblank
note or at least one actual correction. Accepted sections cannot contain
corrections. The caller cannot supply reviewer identity or review thresholds.

Only `ballotTitle` (no candidate index), `ballotLabel` and `partyLabel` are
editable. Candidate indexes are zero-based within the current section. Corrected
labels contain 1–255 characters; parties must match the supported manifest list.
Unknown fields, duplicate/no-op corrections, invalid indexes, empty labels and
duplicate candidate names fail validation. Source citations, keys, geography,
document metadata and candidate membership cannot be changed through this route.

All validation and writes run in one transaction. Corrections create one new
private batch revision, immutable before/after history, and a flag for each
changed section. An acceptance for the corrected text must be a later request.
Clients must use the returned batch ID for subsequent writes; old IDs fail 409.
The original batch and source remain unchanged.

Acceptances carry forward only for fully unchanged sections with identical
source and election/context. Unresolved flags stay visible for the same source.
Each decision exposes `carriedForward`; its `at` stays the original review time.
Each race exposes `corrections` with reviewer, timestamp, note and field-level
before/after values. Carry-forward never revives acceptance from an older,
non-current revision. Unchanged setup reruns preserve browser corrections.

## Compatibility decisions and import

### Shared content and separate county coverage

`reviewStatus` / `approvalCount` describe qualifying **content** reviews. The
additive `localApprovalCount` and `countySourceReviewed` fields distinguish direct
county-page checks from reused content. `matchingCounties` identifies matching
office identities; `sharedReviewBlockedReason` explains a content mismatch or
unresolved flag. `sharedReviews` lists actual donor decision IDs, original
decision IDs, reviewers, timestamps, county, batch ID, race key, printed page and
PDF navigation page. Local `decisions` are not fabricated or prefilled.

Matching is limited to the same publication/document, certified election,
office identity, district and identical content; local/county offices are
county-scoped in this pilot. Only current direct human decisions qualify; one
person in several counties counts once. Disabled reviewers, unresolved flags,
and differing content cannot supply shared approval. See
[shared review rules](SHARED_RACE_REVIEW.md).

Batches expose `sharedReviewedRaces`, `requiresCountyConfirmation`,
`reviewBasisHash`, and `countySourceConfirmedBy`. Shared imports require:

```json
{
  "confirmedCountyCoverage": true,
  "reviewBasisHash": "<64-character hash returned by the current batch>"
}
```

This confirms that the county's listed contests occur on its source pages, not
precinct/voter applicability or a new name-by-name review. No caller-supplied
reviewer identity is accepted. Missing confirmation or stale evidence fails 409
without writes. Fully local reviewed imports remain compatible with an empty
body. The CLI cannot bypass the shared county-coverage confirmation.

The promotion receipt and canonical writes commit together or roll back together.
The immutable receipt retains the exact local/shared basis and authenticated
county confirmer. Imported batches display that historical snapshot, not fresh
approval of subsequent evidence. Existing imports without snapshots are unchanged.

### Existing section-decision endpoint

Example body for the existing `/decisions` endpoint:

```json
{
  "raceKeys": ["a-key-returned-by-the-batch"],
  "decision": "flagged",
  "note": "Candidate label does not match the cited page."
}
```

`decision` is `accepted` or `flagged`. Flags require a nonblank note. Empty,
duplicate or unknown keys fail validation. The latest decision per staff/race
counts; flags block completion, and acceptances from disabled accounts do not
qualify. The caller cannot choose another reviewer or a reviewer count.

Imports require a current, completely reviewed revision and active source
retention approval. Old revisions and imported revisions cannot receive new
decisions. Repeated import of the same completed batch is idempotent. Changes
create another immutable revision, retaining history; changed sections require
review again and unchanged sections can retain their existing reviews as above.
Canonical conflicts stop import instead of silently overwriting prior records.

Errors: 401 unauthenticated/expired; 403 forbidden origin; 404 inaccessible
batch/source; 409 stale, incomplete or conflicting operation; 422 invalid input;
503 unavailable storage/database. Sensitive validation inputs and SQL details
are not returned. The PDF is private even when its original publisher URL is public.

## Limits and tests

Each race keeps `sourcePage` as its printed citation and exposes a separate
`pdfPageNumber` (one-based physical page) for PDF navigation. The retained SOS
2026 certification has an unnumbered cover: printed 271 opens PDF page 272.
That +1 mapping is keyed to the exact document checksum, not applied globally.
Other numeric citations retain same-number navigation; nonnumeric citations or
known out-of-range pages return null and need manual navigation. This display
metadata does not change draft hashes, source citations or saved decisions.

No API in this slice publishes a ballot, approves interviews, rewrites retained
source documents or canonical records, registers users, or claims exact ballot applicability. The generalized
one-/two-review database policy is not a replacement for those future screens.

`test_editorial_api.py` covers access, origin handling, password hashing and
OpenAPI. `test_editorial_corrections.py` covers the field whitelist, validation,
original-value preservation and unchanged-section detection.
`test_editorial_integration.py` covers real database intake, sessions,
revision changes, atomic corrections, preserved reviews, setup reruns, flags,
shared county confirmation, immutable import receipts, import, tenant isolation and current-content review
thresholds. Run it with `docker compose --profile tests run --build --rm api-test`,
which uses a separate temporary PostGIS service, never the pilot database.
Frontend payload tests run with `npm test` from `apps/web` and during the web
Docker build. No new runtime dependency is required.
`test_shared_editorial_reviews.py` covers matching, differences, distinct human
counting and evidence hashes without a database.
