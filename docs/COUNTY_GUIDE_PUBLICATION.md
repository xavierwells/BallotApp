# Publish a reviewed county guide

This slice releases reviewed **candidate certification facts**, not complete or
personalized ballots. It adds the public `/guides` page and versioned read APIs,
plus separate publication controls in the private guide preview.

Operator checkpoint, 2026-09-12: checks reported green and this slice accepted.
No exact new test count or release identifier was supplied; persisted release
receipts remain authoritative. Existing installations do not need repeat review
or publisher grants for the [navigation update](BROWSING_AND_STAFF_NAVIGATION.md).

## Owner decisions

Confirmed on 2026-09-12:

- Only the owner's account may publish or withdraw initially. Publishing access
  can be granted to additional provisioned staff later; ordinary reviewers do
  not acquire it automatically.
- A newer source/draft does not change or hide the published version. An explicit
  publication replaces it; an explicit withdrawal takes it offline. Dates remain
  visible so a release is not presented as a live source check.

Active source approval remains a safety prerequisite for public serving. A
rejected/retired source, revoked retention scope, inactive authority, or changed
source identity hides the affected release even if no withdrawal event exists.
This is not a deletion; an owner can still find and withdraw the recorded release.

## Upgrade and first use

Existing county reviews and imports are reused. Do not repeat extraction,
source download, account setup, or transcription review.

First test against the **separate test database**, never the pilot database:

```powershell
docker compose --profile tests run --build --rm api-test
```

If this is not green, stop before upgrading the pilot. The suite includes the
previous boundary-isolation regression and the new publication integration tests.
Run it a second time against the retained test service to check repeatability.

Back up the pilot database with the existing [backup runbook](OPERATIONS_RUNBOOK.md#postgresql-backup-and-restore).
Then rebuild the regular stack so its migration service applies
`019_county_guide_publication` before the updated API starts:

```powershell
docker compose -f compose.yaml up -d --build
docker compose run --rm api python -m app.cli.editorial_user grant-publisher --username xavier
```

The second command grants only `xavier` publishing access; it does **not** publish
anything, change the password, or create a human review. It revokes existing
sessions, so sign in again. Other accounts start without this capability.
The same operator command supports `revoke-publisher`; neither operation is
available to ordinary web reviewers. Access changes retain a database-role audit
record, not an invented human-review identity. No username is hard-coded in the
authorization logic.

At [the private preview](http://localhost:3000/editorial/preview):

1. Choose an imported county. The publication panel rechecks its evidence and
   reports a blocker if source approval, saved reviews, or canonical citations
   no longer qualify. It does not create a new verification date or require a
   duplicate review when the existing evidence still qualifies.
2. Check the explicit official-fact release confirmation, then select **Publish
   county guide** and confirm the browser prompt. An already-live revision cannot
   be published again accidentally. A later revision uses **Replace published
   guide** with the same explicit confirmation.
3. Open the public link, or visit [county guides](http://localhost:3000/guides)
   without a staff session. Public content includes names, offices, parties,
   source attribution/page links, source dates and historical content-review dates.
4. To remove it, expand **Take the published guide offline**, enter a private
   reason, and confirm **Withdraw published guide**. No release, review or source
   is deleted. Old links return 404; older releases do not reappear as a fallback.

**Manage published releases** remains available when a newer draft hides the old
import from the normal list or a canonical conflict prevents the preview from
loading. Its publication panel can still withdraw the live release.

An interrupted/failed write is never retried automatically. Refresh publication
status before retrying: a response can be lost after the database commits.
Stale page/state tokens produce 409 rather than overwriting another action.

## What remains private or separate

- The retained PDF, storage keys, extraction drafts, reviewer usernames, staff
  identities, decision notes, county confirmation identities and withdrawal
  reasons are not in public payloads. Public PDF links go to the original
  publisher, never the protected editorial download endpoint.
- The existing narrow official-fact policy permits attributed facts/metadata,
  not a PDF mirror, expressive reuse, candidate applications or personal data.
  Private retention approval alone is **not** a publication action or blanket
  license grant. The publisher makes the explicit release decision under that
  recorded policy. Express restrictions, objections or material legal concerns
  still require escalation under [Guardrails](GUARDRAILS.md).
- County-wide certification does not establish which races apply to an address.
  Both public contracts and UI state `exactMatch: false`, `completeBallot: false`.
  Missing local races, propositions, ballot styles and voting information are
  disclosed. No `ballot_versions` or claim-publication gates are bypassed.
- New canonical corrections still require the controlled reconciliation/import
  workflow. A release is a frozen copy; later edits cannot silently rewrite it.
  Historical releases are retained privately; a public historical archive is
  not enabled in this slice.
- Search stays in page memory; no voter account, address, location, browser
  storage or analytics are introduced. Public fetches omit staff credentials.
- Publication is distinct from internet deployment. No DNS, hosting, provider,
  or production deployment changes are made by these controls.

## API and persistence

Swagger/OpenAPI/ReDoc describe the requests, responses, authorization and errors.

| Endpoint | Access and behavior |
| --- | --- |
| `GET /api/v1/editorial/guide-preview/{batch_id}/publication` | Staff readiness, blockers, capability and current release/event identifiers. |
| `GET /api/v1/editorial/guide-releases` | Staff management list, up to 100 recorded live releases, independent of current preview availability. |
| `POST /api/v1/editorial/guide-preview/{batch_id}/publish` | Publisher + trusted origin + confirmation + current evidence/state tokens. |
| `POST /api/v1/editorial/guide-releases/{release_id}/withdraw` | Publisher + trusted origin + current state token + confirmation/private reason. |
| `GET /api/v1/guides` | Public list, `offset` (0–10000) / `limit` (1–50; default 20), `hasMore`; optional exact county-label filter; configured pilot publication only. |
| `GET /api/v1/guides/{release_id}` | Public frozen release; generic 404 for missing, withdrawn, superseded or inaccessible records. |

Staff responses use `no-store, private`; public guide responses use `no-store` so
our browser/proxy paths do not cache a withdrawn response. This cannot recall
copies already read or saved by someone else. Shared CDN caching is not enabled.
General API rate limits and request IDs remain deployment/backlog work; do not
advertise them as implemented by this slice.

The public scope reuses `BALLOT_BROWSE_ORGANIZATION_SLUG` and
`BALLOT_BROWSE_PUBLICATION_SLUG`, with the existing pilot defaults. Clients cannot
select an arbitrary private tenant. The public page lists only explicit releases;
until one is published it shows an honest empty state, not demo or private data.

Migration 019 adds a default-deny publisher capability, its append-only change
audit, immutable `county_guide_releases`, and append-only `county_guide_events`.
Composite foreign keys enforce publication/import/actor scope; triggers enforce
active publisher identity and prevent update/delete of release/event history.
The application admission service serializes with intake/review/import on the
publication lock, checks live review eligibility and unchanged canonical facts,
validates retained source bytes, and constructs a typed public-field allowlist.
Review eligibility is not inferred from a Markdown approval or an API client field.

## Verification and operator acceptance

Local checks: 183 API tests passed, 17 database tests skipped, one existing
Starlette/httpx warning; 31 frontend tests passed; production web build and
migration-019 offline SQL generation passed. Offline SQL generation is not a
PostgreSQL execution test. Docker execution remains unavailable in the assistant's
shell. The operator subsequently reported green checks and accepted this slice;
future changes still need the isolated integration command above.

The browser checks use synthetic API responses, not the real database. They
exercise explicit confirmation/cancel, publication, public search and citations,
mobile layout, withdrawal, withdrawal despite preview conflict, publisher denial
and session expiry. They never submit reviews or publish the operator's records.

Operator checklist after the isolated suite is green:

- Confirm migration 019 and sign in again after the one-time publisher grant.
- Before publishing, `/guides` must expose no private imports.
- Publish one chosen county; compare its names/parties and publisher page links.
- Open the public guide signed out. Confirm it has no staff names/private notes
  and plainly says it is not a complete or exact personal ballot.
- Confirm a release remains unchanged when new drafts are staged. Withdraw only
  if you intend to take it offline, then confirm its public link is unavailable.

The owner accepted both the private preview and the publication slice. This does
not authorize this agent to perform future human reviews or publication actions.
