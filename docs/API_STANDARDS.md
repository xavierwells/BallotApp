# API standards

The platform will expose multiple APIs: public ballot data, editorial/admin operations, and later partner/data-license APIs. They share one contract discipline but not necessarily one authorization policy.

## API families

| Family | Path | Audience | Data rule |
| --- | --- | --- | --- |
| Public civic | `/api/v1` | voters and integrators | published, sourced data only |
| Editorial | `/api/v1/editorial` | authorized staff | tenant-scoped, auditable; never public merely because it is under `/api/v1` |
| Partner | `/api/partner/v1` | contracted clients | explicit license and rate limits |

## Baseline conventions

- JSON request and response bodies use `camelCase` at public boundaries.
- Resource names are plural nouns; actions are exceptional and documented.
- Use UTC ISO-8601 timestamps, UUID identifiers, cursor pagination, and a documented error response model.
- Require an `X-Request-ID` on responses and accept a caller-provided value after validation.
- Public APIs are read-only until an authorization design is approved.
- Swagger UI is a discovery/testing tool, not a replacement for versioned OpenAPI contracts and human documentation.
- Browser-facing write requests must have an explicit CORS-preflight test; API
  unit tests alone cannot prove the browser can call an endpoint.

The implementation includes health, non-persisting ballot resolution/browsing,
authenticated editorial review, and staff-only imported-certification preview.
The private guide's GET endpoints are documented in
[`PRIVATE_GUIDE_PREVIEW.md`](PRIVATE_GUIDE_PREVIEW.md); neither a certification
nor a geographic browse estimate determines a voter's ballot. Publication is a
separate gated workflow. Some baseline conventions (including generalized cursor
pagination and request IDs) remain delivery targets, not completed guarantees.

The [county-guide publication slice](COUNTY_GUIDE_PUBLICATION.md) adds publisher-only
release/withdraw actions and public `/api/v1/guides` reads from immutable, explicitly
published snapshots. It uses bounded offset pagination for this pilot, not the
eventual generalized cursor contract. Public source copies, reviewer identities,
private notes and exact-ballot claims are excluded. No-store responses preserve
withdrawal behavior without introducing shared CDN caching.

The [navigation slice](BROWSING_AND_STAFF_NAVIGATION.md) adds the optional
`county` query parameter to `GET /api/v1/guides`: a full-label, case-insensitive,
outer-whitespace-trimmed directory filter, never fuzzy geography or a personal
ballot match. It keeps the existing public projection and publication/source
gates. Staff login/site map reuse the existing editorial login/me/logout APIs;
navigation creates no roles or permissions.

Search hardening: `/api/v1/ballots/browse` accepts ASCII ZIP or ZIP+4; ZIP+4
is explicitly reduced to its five-digit coarse area in the response query and
message. Address requests trim outer whitespace before minimum-length
validation. Neither change stores voter inputs or relaxes exact-ballot gates.
See [search verification and current coverage limits](SEARCH_VERIFICATION.md).
