# API standards

The platform will expose multiple APIs: public ballot data, editorial/admin operations, and later partner/data-license APIs. They share one contract discipline but not necessarily one authorization policy.

## API families

| Family | Path | Audience | Data rule |
| --- | --- | --- | --- |
| Public civic | `/api/v1` | voters and integrators | published, sourced data only |
| Editorial | `/api/editorial/v1` | authorized staff | tenant-scoped, auditable |
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

The scaffold intentionally offers only liveness/readiness and a non-persisting, POST-only ballot-resolution preview. It does not claim to determine a voter’s ballot.
