# Ballot discovery API contract

Epic 3 defines ballot discovery before connecting a geocoder or importing real
boundaries. The API is available in Swagger at `/docs` and under `/api/v1`.

## Address resolution

`POST /api/v1/ballots/resolve` accepts one request-scoped `address`. The address
is discarded and never appears in the response. The existing
`/resolve-preview` route remains temporarily as a deprecated alias.

The response is a discriminated union selected by `status`:

| Status | Meaning | Ballot payload |
| --- | --- | --- |
| `resolved` | One ballot is supported by authoritative ballot and boundary evidence. | Exactly one ballot with confidence, geographic support, and citations. |
| `ambiguous` | The location is on/near a boundary or otherwise supports multiple results. | At least two distinct plausible ballot versions with explanations. |
| `source_conflict` | Authoritative boundary or ballot-style sources support different results. | At least two distinct plausible ballot versions, each retaining its supporting source. |
| `needs_review` | Evidence is insufficient for a final result but may identify possibilities. | Zero or more plausible ballots plus official contact links. |
| `not_found` | No evidence-backed ballot candidate was found. | No ballot; explanatory message and official contact links. |
| `not_available` | The provider, reviewed election context, or required published evidence is unavailable. | No ballot; the pipeline fails closed rather than guessing. |

Reason codes are stable machine-readable values such as
`low_geocode_confidence`, `near_boundary`, `boundary_source_conflict`, and
`ballot_data_unavailable`. Human-facing explanations remain separate.

The contract uses a list for plausible ballots and does not impose a maximum.
That preserves all evidence-backed candidates. Whether a future screen displays
more than two at once or progressively reveals them remains a product decision.

## Coarse ballot browsing

`GET /api/v1/ballots/browse?areaType=city&query=Copperas%20Cove` supports three
area types:

- `zip`
- `city`
- `county`

Every browse response contains `exactMatch: false`. An available result lists
ballots whose supported geography is within or overlaps the selected area. The
user chooses a ballot to inspect; the application does not claim that it is the
user's assigned ballot. Browse mode does not invoke address resolution and is
not a silent fallback from a failed address request.

Responses also carry an explicit `demonstration` flag. In development demo
mode, the endpoint returns two invented overlap matches for interface review.
Outside demo mode it returns `not_available` until verified ballots and real
ZIP/city/county area indexes exist. ZIP input is restricted to ZIP or ZIP+4;
the endpoint never accepts an address-shaped value as a ZIP browse query.

Available matches are explicitly ranked. A percentage-based ordering records
`estimatedAreaSharePercent`, a calculation basis, and a source citation; the
API rejects an unsourced estimate. The first sourced estimate may be labeled
`mostCommonAreaMatch`, which describes the selected area's residential
population or address coverage—not the probability that a particular ballot
belongs to the user. Alternatives remain visible. Land-area estimates are
supported for provenance but should not drive a “most common” label when a
residential estimate is available.

Before official ballot versions are connected, an available response may carry
`areaMatches` instead of ballot `matches`. Each area match identifies the
reviewed county or other civic area, rank, percentage, calculation basis, and
all coverage-source citations. The message explicitly states that no ballot
was selected. Database-backed browse reads are publication-scoped and require
the operator to enable `BALLOT_BROWSE_DATABASE_ENABLED` after promotion.

## Evidence carried by a ballot choice

Each ballot choice identifies an immutable ballot version, election name/date,
and official ballot citation. Geographic support additionally identifies the
named area, boundary version, explanation, authority, source URL, and check
time. This makes an exact or unresolved result auditable without storing the
voter's address or coordinate.
