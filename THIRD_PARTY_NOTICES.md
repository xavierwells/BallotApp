# Third-party notices and approval ledger

Only the components listed below are approved for the initial scaffold. This is not a substitute for a lockfile-level SBOM and license scan in CI.

| Component | Purpose | License | Approval basis |
| --- | --- | --- | --- |
| FastAPI | API framework and OpenAPI/Swagger generation | MIT | [upstream project metadata](https://github.com/fastapi/fastapi/blob/master/pyproject.toml) |
| Next.js | web framework | MIT | [upstream package metadata](https://github.com/vercel/next.js/blob/canary/packages/next/package.json) |
| React | UI runtime | MIT | upstream project license |
| PostgreSQL | relational database | PostgreSQL License | [official license](https://www.postgresql.org/about/licence/) |
| Valkey | optional cache and future queue broker | BSD-3-Clause | [upstream project](https://github.com/valkey-io/valkey) |
| Uvicorn | ASGI server | BSD-3-Clause | upstream project license |
| Pytest | test runner | MIT | upstream project license |
| HTTPX | API test-client dependency | BSD-3-Clause | upstream project license |
| TypeScript and DefinitelyTyped packages | compile-time web types | Apache-2.0 / MIT | upstream project licenses |
| pip-audit | Python dependency vulnerability scanner | Apache-2.0 | [upstream project](https://github.com/pypa/pip-audit) |
| Trivy | vulnerability, secret, misconfiguration, license, image, and SBOM scanner | Apache-2.0 | [upstream project](https://github.com/aquasecurity/trivy) |
| GitHub checkout action | CI source checkout | MIT | [upstream project](https://github.com/actions/checkout) |

## Pending approval template

| Field | Required value |
| --- | --- |
| Name / version | |
| Type | library, image, API, dataset, map tile, or source |
| Owner / provider | |
| Purpose | |
| License or terms URL | |
| Cost and rate limits | |
| Permitted commercial use | yes/no/evidence |
| Address/PII sent or retained | yes/no/details |
| Attribution / redistribution requirements | |
| Reviewer and date | |
| Decision | approved, rejected, or exception |
