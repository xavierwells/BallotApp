# What's on My Ballot

An open, nonpartisan civic-information platform. This repository begins with a portable web and API foundation for the Copperas Cove pilot while retaining a path to hosted multi-tenant and self-hosted installations.

## Included

- `apps/web` — public Next.js frontend.
- `apps/api` — versioned FastAPI service with generated OpenAPI, Swagger UI, and ReDoc.
- `compose.yaml` — local and single-server container stack.
- `compose.production.yaml` — conservative production overrides.
- `infra/kubernetes` — Rancher-compatible standard Kubernetes manifests.
- `docs` — privacy, API, testing, license, and deployment standards.

No civic-data or geocoding provider is connected yet. The address endpoint is a deliberately non-persisting preview so that privacy is a verified rule before a provider is selected.

## Start the stack

1. Copy `.env.example` to `.env` and set a strong database password.
2. Run `docker compose up --build`.
3. Open the web app at `http://localhost:3000`.
4. Open Swagger UI at `http://localhost:8080/docs`.

Run API and OpenAPI contract tests with `make api-test` (or the equivalent Docker commands in [`Makefile`](Makefile)).

Read [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) for bare-metal and Rancher/Kubernetes deployment.
The staged product plan and current implementation priority are in [`docs/PRODUCT_DELIVERY_BACKLOG.md`](docs/PRODUCT_DELIVERY_BACKLOG.md).
Quality gates and operational standards are in [`docs/CI_QUALITY_GATES.md`](docs/CI_QUALITY_GATES.md), [`docs/OPERATIONS_RUNBOOK.md`](docs/OPERATIONS_RUNBOOK.md), and [`docs/ACCESSIBILITY.md`](docs/ACCESSIBILITY.md).

## Non-negotiable rules

- Do not store entered addresses or other voter PII.
- Every API change updates the OpenAPI contract and automated tests.
- Every dependency, data source, and external API passes the review process in [`docs/GUARDRAILS.md`](docs/GUARDRAILS.md) before use.
- Only permissive, commercially usable dependencies are allowed by default.
