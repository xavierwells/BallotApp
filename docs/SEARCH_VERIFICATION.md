# Search verification checkpoint — 2026-09-12

Scope: public ZIP/city/county discovery, address/location request handling,
and candidate/office/party filtering within an opened guide. No new geocoder,
typeahead provider, geographic evidence, review or publication was added.

## Findings

- The live API returned Bell, Coryell and Lampasas releases. ZIP 76522 returned
  the reviewed Coryell 94.7766% / Lampasas 5.2234% geographic estimates.
- The live API's OpenAPI schema lacked `county` on `/api/v1/guides`; even
  `county=Missing County` returned all three guides. This proves that the API
  image had not received the preceding navigation update. Rebuilding only the
  website does not update Python code. Keep the mismatch guard; do not display
  those counties as matches or reset/review/publish the data again.
- ZIP+4 passed validation but was looked up as a complete string against the
  five-digit area index. `76522-1234` returned not found while `76522` worked.
- The homepage did not cancel pending requests when changing inputs or modes.
  Old responses could repopulate a cleared screen; a late browser-location fix
  could still be submitted after switching away.
- Whitespace-only addresses passed the minimum-length check. Multiple spaces
  also broke otherwise identical candidate/office phrase searches.

## Changes

- ZIP+4 looks up its five-digit area. The API returns that five-digit query and
  explicitly explains the coarse scope. It never treats the extension as an
  exact address, precinct or ballot. The web form accepts outer whitespace;
  invalid ZIP formats are still rejected, not fuzzy-matched.
- County search queries published guides directly. It no longer first displays
  a geographic-coverage failure above an available county guide. Full-label
  matching and the optional County suffix remain; no city-to-county inference.
- ZIP is the initial area-search mode. City mode explains that reviewed city
  coverage is not connected and offers the separate county directory.
- Editing an input, changing area type/mode, leaving the page or starting a new
  search invalidates old callbacks. Type changes clear the old query. Submitted
  addresses clear immediately; an old request cannot erase newly typed text.
- Search requests and county-directory requests time out after 15 seconds.
  Retry is manual; failures do not select a ballot or revive earlier results.
  Browser cancellation cannot retract a request already received by a server.
- Address validation trims outer whitespace before applying length limits.
  Validation responses still omit submitted values. Guide phrase searches ignore
  repeated whitespace/case without changing source text, order or race rosters.

No voter input was used to test geocoding. Address/location failures, delayed
callbacks and error recovery were exercised with synthetic responses only.
Exact address-to-ballot accuracy still depends on verified election styles and
boundaries; this checkpoint does not certify those external data dependencies.

## Verification

- API: **201 passed, 17 skipped, 1 existing warning**. The skipped tests require
  the isolated PostgreSQL test service; no pilot database reset is permitted.
- Frontend: **40 passed**; production build passed.
- Mocked browser checks: stale city/address responses, late location callbacks,
  ZIP whitespace, direct county search, service failure/retry, candidate/party/
  district filters, full opponent rosters, no-match/clear and mobile layout.
- Staff login/site-map and area-to-guide navigation regression checks passed.
- A separate read-only browser check against the running site's real Coryell
  guide passed: 36 races, candidate/party/district phrase filters, no-match,
  clear-search and complete candidate rosters. Search terms stayed in the page;
  filtering made no new API requests. This checks behavior against published
  records, not independent certification of their factual accuracy.
- Public HTTP checks above were read-only. No accounts, releases or reviews
  were modified. Docker execution remains denied in the assistant's shell.

## Operator update and acceptance

From `D:\BallotApp`, first test, then rebuild **both** application services:

```powershell
docker compose --profile tests run --build --rm api-test
docker compose -f compose.yaml up -d --build --no-deps api web
```

Migration 019 is the prerequisite already used for publication; this slice adds
no migration or dependency. Do not rerun extraction, review, grant or publish.

| Try | Expected result |
| --- | --- |
| ZIP `76522` | Reviewed county area estimates and available published-guide links; no exact ballot claim. |
| ZIP `76522-1234` | Same five-digit area evidence, with an explicit ZIP+4 explanation. |
| County `Coryell` or ` coryell county ` | Only published Coryell guides, without the unrelated geographic-coverage warning. |
| An unlisted county | No published guide for that county; not proof of no election. |
| City `Copperas Cove` | Honest missing-city-coverage message; separate county directory remains available. |
| Candidate, party or district in an opened guide | Matching races keep their full candidate rosters; clearing restores the full guide. |
| Change mode during a slow lookup | No late result under the new mode; no late location submission. |

To confirm the running API was rebuilt, its Swagger `/api/v1/guides` operation
must include `county`. A direct request with `county=Coryell County` must return
only that county. No API filter is evidence of personal voter applicability.
