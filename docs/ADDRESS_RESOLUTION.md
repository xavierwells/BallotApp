# Address and jurisdiction resolution

The address-to-ballot engine must favor a transparent “not confident” response over a guessed ballot.

## Two-stage design

```text
Ephemeral address
  → approved geocoder adapter
  → coordinates + geocode confidence
  → self-owned PostGIS boundary resolution
  → authoritative ballot-style/version match
  → ballot or an explicit uncertain result
```

Geocoding and jurisdiction resolution have distinct responsibilities:

- A **geocoder adapter** converts an address to coordinates. Before adoption, the provider's terms, license, privacy/retention behavior, availability, and rate limits must be recorded in the approval ledger. The Census Geocoder is a candidate for evaluation, not an approved dependency.
- The **jurisdiction resolver** is owned by the platform. It runs point-in-polygon checks against versioned official precinct, county, school-district, legislative, and special-district boundaries stored in PostGIS.
- The **ballot matcher** selects a verified official ballot style/version. Geographic matching alone is never sufficient evidence of the final ballot.

## Confidence and ambiguity rules

Every resolution must carry `resolutionStatus`, `confidence`, `boundaryVersionIds`, and `reasonCodes`.

| Situation | Required behavior |
| --- | --- |
| Low-confidence geocode or unmatched new address | Return `needs_review`; do not guess or fall back to ZIP code. |
| Point on/near a jurisdiction boundary | Mark `ambiguous`; evaluate all applicable boundary versions and do not publish a ballot unless the authoritative ballot style resolves it. |
| Authoritative boundaries disagree | Mark `source_conflict`; retain both source versions and require editorial resolution. |
| Verified ballot style matches | Return `resolved` with the ballot version and its source evidence. |

Because the platform does not retain addresses, `needs_review` cannot create a queue containing a raw address. The user receives a clear uncertainty response and official election-authority contact path. A future opt-in support workflow would require a separate privacy review before accepting any address.

## Data refresh and audit

Boundary records are versioned, never overwritten. Each import captures authority, source URL, retrieval time, effective date, geometry checksum, and reviewer. Refresh on official redistricting/precinct notices and, during an active election, follow the election verification cadence in the launch plan.
