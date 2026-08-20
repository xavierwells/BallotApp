# Development guardrails

These are release requirements, not aspirations. A pull request that fails a mandatory rule must not ship without a recorded exception approved by the project owner.

## License and external-resource review

Before adding a library, container image, API, dataset, map tile provider, or scraped source, record it in `THIRD_PARTY_NOTICES.md` or the source registry.

Required fields: owner, purpose, direct source URL, license/terms URL, cost model, rate limit, retention rules, attribution requirement, redistribution rights, and reviewer/date.

Allowed by default: Apache-2.0, MIT, BSD-2/3-Clause, ISC, PostgreSQL License, CC0, and public-domain material. Other licenses—including copyleft, source-available, non-commercial, research-only, share-alike, or custom terms—require written legal/product approval before introduction. A "free tier" is not a license determination.

No provider may receive an entered voter address until its terms, privacy terms, allowed use, retention policy, and cost/rate limits have passed review.

`scripts/check_direct_dependency_approvals.py` must run in CI and fails when a direct application dependency is absent from `governance/dependency-approvals.json`. Update the approval record and `THIRD_PARTY_NOTICES.md` in the same change as every new dependency.

## API contract first

- Every public endpoint lives under `/api/v{major}`.
- FastAPI-generated `/openapi.json`, `/docs` (Swagger UI), and `/redoc` are published for every running environment except where access policy forbids it.
- Route descriptions, request models, responses, errors, auth requirements, pagination, and examples are part of the contract.
- Backward-incompatible changes require a new major API version and migration notice. Do not silently repurpose fields.
- The OpenAPI file is a build artifact and must be checked in CI for breaking changes before any public API is released.

## Testing

- Every endpoint gets at least success, validation/error, and authorization tests as applicable.
- Contract tests must assert that the endpoint appears in OpenAPI.
- Add integration tests for persistence, provider adapters, queues, and authorization before those components are enabled.
- Tests must use synthetic addresses and civic records only. Never use real voter or contributor data as fixtures.

## Privacy and data minimization

- An entered address is request-scoped input, not a user profile field.
- It must not be persisted in application databases, analytics, logs, error reporting, queues, URLs retained by the frontend, or support tickets.
- Clear the frontend field after use; return a ballot-result identifier, never echo the address.
- Do not collect voter registration, party, vote history, government-issued ID, or precise location unless a separately approved requirement and privacy review permits it.
- Production logging must redact address-like fields and request bodies for ballot-resolution endpoints.

## Evidence and editorial integrity

- Published civic claims require a source, retrieval date, source type, and editorial status.
- Preserve original public documents and page-level citations where permitted.
- AI output is a research draft, never an authority or publish trigger.
- Separate fact, candidate statement, editorial analysis, and community tip in both data and UI.

## Operational security

- No credentials in source, images, or committed `.env` files.
- Use non-root application containers and read-only filesystems where feasible.
- Pin release dependencies and container image digests before production.
- Run dependency, container, secret, and license scans in CI before deployment.
- Keep database and cache ports private in production.
- Follow the secret, backup/restore, incident, correction, and accessibility procedures in `OPERATIONS_RUNBOOK.md` and `ACCESSIBILITY.md`.
