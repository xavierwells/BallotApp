# Address and jurisdiction resolution

The address-to-ballot engine must favor a transparent “not confident” response over a guessed ballot.

The product also supports a separate **browse mode** for people who do not want
to enter an address. Browse mode lists available ballots by ZIP code, city, or
county, but never claims that one of those ballots is the voter's exact ballot.
A ZIP code or municipality may cross precinct, district, county, or ballot-style
boundaries, so the voter chooses which ballot to inspect.

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

- A **geocoder adapter** converts an address to coordinates. The Census Geocoder is approved for opt-in, ephemeral, server-side pilot use under the controls in [`GEOCODER_APPROVAL.md`](GEOCODER_APPROVAL.md). It is disabled by default and is not evidence of ballot assignment by itself.
- The **jurisdiction resolver** is owned by the platform. It runs point-in-polygon checks against versioned official precinct, county, school-district, legislative, and special-district boundaries stored in PostGIS.
- The **ballot matcher** selects a verified official ballot style/version. Geographic matching alone is never sufficient evidence of the final ballot.
- A ballot style is defined by a verified **combination** of required geographic
  areas, not by one hard-coded precinct field. Every requirement must be in the
  resolved membership set; unrelated extra memberships are allowed. Zero or
  multiple matching published ballot versions are explicit non-results.

## Confidence and ambiguity rules

Every resolution must carry `resolutionStatus`, `confidence`, `boundaryVersionIds`, and `reasonCodes`.

| Situation | Required behavior |
| --- | --- |
| Low-confidence geocode or unmatched new address | Return `needs_review`; do not guess or fall back to ZIP code. |
| Point on/near a jurisdiction boundary | Mark `ambiguous`; evaluate all applicable boundary versions. Return the plausible ballot choices with plain-language descriptions of the geography that makes each one applicable. Do not label either choice as the voter's resolved ballot. |
| Authoritative boundaries disagree | Mark `source_conflict`; retain both source versions and show the ballots supported by each source with their citations and an explicit conflict warning. |
| Verified ballot style matches | Return `resolved` with the ballot version and its source evidence. |

The initial self-owned resolver implements exact PostGIS `ST_Covers` checks
against active areas and verified boundary versions effective on the election
date. An exact geometric edge is `ambiguous`; overlapping interiors for the
same authority and area type are a `source_conflict`. A configurable
"near-boundary" distance is deliberately not guessed and remains a later
product/operational decision.

Because the platform does not retain addresses, `needs_review` cannot create a queue containing a raw address. The user receives a clear uncertainty response and official election-authority contact path. A future opt-in support workflow would require a separate privacy review before accepting any address.

## Browse mode versus address resolution

| Path | What the user provides | What the product may claim |
| --- | --- | --- |
| Browse by ZIP, city, or county | A coarse place selected by the user | “These ballots are available in or overlap this area; choose one to view.” |
| Resolve an address | A request-scoped address that is discarded | Either one evidence-backed exact ballot, or an explicitly unresolved set of plausible ballots. |

Browse mode is not a fallback that silently turns an unresolved address into a
ZIP-level match. The interface must visibly switch modes and explain the lower
precision. Neither mode stores the entered address or associates browsing with
a voter profile.

## Data refresh and audit

Boundary records are versioned, never overwritten. Each import captures authority, source URL, retrieval time, effective date, geometry checksum, and reviewer. Refresh on official redistricting/precinct notices and, during an active election, follow the election verification cadence in the launch plan.
