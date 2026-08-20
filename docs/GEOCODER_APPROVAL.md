# Geocoder approval — U.S. Census pilot adapter

**Decision date:** 2026-08-20  
**Decision:** Approved for opt-in, ephemeral, server-side pilot use with the
controls below. Disabled by default in every deployment.

## Approved resource

| Field | Decision record |
| --- | --- |
| Provider | U.S. Census Bureau |
| Service | Single-record Census Geocoding Services API |
| Purpose | Convert a voter-submitted U.S. structure address to a temporary coordinate; BallotApp performs its own authoritative boundary matching afterward. |
| Documentation | <https://geocoding.geo.census.gov/geocoder/Geocoding_Services_API.html> |
| Terms | <https://www.census.gov/data/developers/about/terms-of-service.html> |
| Privacy | <https://www.census.gov/about/policies/privacy/privacy-policy.html> |
| Cost | No charge documented for the public service; availability is as-is and may be limited or terminated. |
| Rate limits | No numeric single-record limit is documented. The terms reserve the right to limit or block use. BallotApp therefore makes one request per user submission, with no retries or batch use. |
| Input sent | Full structure address over HTTPS from the BallotApp API server. No user ID, session ID, browser IP, cookie, or BallotApp profile field is sent. |
| Retention finding | The geocoder-specific documentation does not promise deletion. Census's general policy says system logs can be retained indefinitely. Approval therefore does not claim that no third party receives or retains the address. |
| BallotApp retention | None: no address, provider response, normalized address, or coordinate is written to a database, cache, queue, analytics system, log, URL returned to the browser, or support workflow. |
| Attribution | Display: “This product uses the Census Bureau Data API but is not endorsed or certified by the Census Bureau.” |
| Commercial use | Terms allow development of services using the API and do not restrict the application's commercial status, subject to the complete terms. |
| Reviewer | Product owner and project implementation review, 2026-08-20 |

## Mandatory controls

1. The browser sends the address only to BallotApp. Census calls are
   server-to-server so the provider sees the BallotApp server IP, not the
   voter's browser IP or cookies.
2. `GEOCODER_PROVIDER` defaults to `disabled`; operators explicitly select
   `census` after accepting this approval and displaying the disclosure.
3. Requests use HTTPS, a five-second default timeout, one attempt, and no cache.
4. Request bodies, outbound provider URLs, provider responses, normalized
   addresses, and coordinates must not be logged.
5. The adapter extracts only match state, coordinate, provider name, and Census
   benchmark. It discards the response's echoed/normalized address.
6. Ambiguous and unmatched responses remain unresolved. They never trigger a
   ZIP fallback or a guessed ballot.
7. Provider terms and privacy language are manually re-reviewed at least
   annually and before a new tenant enables the adapter.
8. Self-hosted operators may leave external geocoding disabled. A future local
   geocoder requires its own data, license, update, and accuracy review.

## Accuracy boundary

The Census service calculates coordinates from MAF/TIGER address ranges; its
result is not evidence of ballot assignment. BallotApp will use the coordinate
only as input to its own versioned official-boundary resolver. A single match
does not become `resolved` until the authoritative ballot-style matcher also
succeeds.

The adapter and tests are present, but `/api/v1/ballots/resolve` remains
`not_available` until official pilot boundaries and ballot-style relationships
are loaded. Tests use invented addresses and provider responses and never call
the live Census service.

