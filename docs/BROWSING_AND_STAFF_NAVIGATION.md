# County guide browsing and staff navigation

This slice connects existing public releases to the entry page. It does not
publish records, change reviews, add a migration, grant accounts, or change
address-to-ballot decisions. Already-imported corrections/supersession remain
deferred by the owner; withdrawal is available if a material error is found.

## Public journey

- Choose **Browse without an address** to see published county guides. Each link
  names the county and election; nothing is selected automatically.
- Reviewed county area cards (including those returned for ZIP 76522) look up
  currently published guides by the county's full label. Geography sources,
  ranks and percentages remain unchanged. A population share is not the chance
  a particular ballot applies to a person.
- An explicit county search may omit the word "County"; the UI adds that display
  suffix. The API matches the full label, ignoring only case and outer
  whitespace, within the operator-configured publication. No fuzzy matching,
  hard-coded ZIP mapping or inferred city coverage is introduced.
- County searches now go directly to that published directory; they do not
  depend on geometric county browsing. ZIP+4 uses only the five-digit area and
  explains that limitation. See [search verification](SEARCH_VERIFICATION.md).
- Synthetic area cards never link their invented geography to real releases.
  The general directory remains separately labeled as published information.
- Failed/unresolved address lookups offer a plain `/guides` link. It does not
  forward or infer a county from the submitted address or coordinates.
- Missing guides and service failures are different states. A missing guide
  does not mean there is no election. Clicking a replaced/withdrawn release shows
  the existing unavailable message, never a private draft or old fallback.
- Guide fetches omit staff credentials and use `no-store`. No browser storage,
  analytics or voter data retention is added. Page restoration rechecks links.
- The web UI rejects mismatched county responses (including an older API that
  ignores the filter), instead of attaching another county's guide to a result.

The directory initially shows up to 20 releases and links to the paginated guide
page. Multiple elections remain separate choices, not a guessed current election.
County-label navigation is not a durable geographic-identity mapping for future
multi-state publications; that belongs with authoritative ballot applicability.

## Staff journey

1. Use **Staff login** at the bottom of the homepage.
2. Sign in with the existing editorial username/passphrase. Login always leads
   to `/editorial/site-map`, including login from the older review page. An
   already-signed-in visitor to `/editorial/login` goes straight to the site map.
3. Choose **Review official facts**, **Preview and publishing**, a public page,
   or API references. Review and preview headers link back to the site map.
4. Sign out from the site map, review workspace or preview. Returning to the
   site map after logout requires sign-in again.

The site map is a navigation page, not a new role or permissions system. It
checks `/api/v1/editorial/me` before showing the authenticated view; all private
data and actions still require the API's existing authorization. Ordinary
reviewers can open preview but cannot publish without an explicit grant. No
account is created by adding the footer link. Editorial routes request no search
indexing; their static shells contain no staff records or credentials.

Login uses the existing cookie/session and trusted-origin controls. Passwords
are cleared from the form and request variables after submission. There is no
arbitrary return-URL parameter, local-storage token, or automatic write retry.

## API addition

`GET /api/v1/guides?county=Coryell%20County&offset=0&limit=20`

`county` is optional, 1–255 characters, and compares a full county label. The
existing response, bounded pagination, tenant scope, active source approval and
latest explicit release gates are unchanged. OpenAPI/Swagger/ReDoc include this
parameter. This is a directory filter, not a ballot-resolution endpoint.

## Test and install

With migration 019 already applied, run the isolated suite, then rebuild just
the two changed application services from `D:\BallotApp`:

```powershell
docker compose --profile tests run --build --rm api-test
docker compose -f compose.yaml up -d --build --no-deps api web
```

No repeat source download, review, publisher grant or publication is needed.
For first-time installation or an older schema, use the full Compose command
in the [publication runbook](COUNTY_GUIDE_PUBLICATION.md) instead.

Acceptance: try ZIP 76522, click a published county guide, and confirm it remains
labeled county-wide/not your exact ballot. Try a county with no release. Then
use the footer login, check the site map links, and sign out. Full city coverage
and exact ballot styles remain separate data work.

Local verification: 189 API tests passed, 17 database tests skipped, one existing
Starlette/httpx warning; 36 frontend tests passed; production build passed.
Mocked browser checks cover staff sign-in/failed login/site map/navigation,
reviewer permissions, session recheck/logout, directory/ZIP/county links,
unresolved fallback, absent/withdrawn/service-error states and mobile layout.
No real account, review, import, release or voter data was changed during QA.
The new PostgreSQL filter assertions remain pending the isolated operator run.
