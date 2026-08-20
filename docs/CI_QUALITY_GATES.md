# CI quality gates

The repository includes `.github/workflows/ci.yml` as a reference GitHub Actions workflow. Its tools are open-source and listed in `THIRD_PARTY_NOTICES.md`. Before enabling it, the deployment owner must record whether runner minutes are hosted, self-hosted, or otherwise funded; hosted CI is an operational cost decision, not an assumed free service.

## Required gates

| Gate | Purpose | Failure behavior |
| --- | --- | --- |
| Direct-dependency approval | Ensures a new direct package has a recorded license/terms decision | blocks merge |
| API contract tests | Tests OpenAPI publication, validation, and browser CORS preflight | blocks merge |
| Web build from lockfile | Ensures the public frontend resolves reproducibly | blocks merge |
| Python and npm audits | Detects known dependency vulnerabilities | blocks on the configured severity |
| Trivy filesystem scan | Detects secrets, insecure configuration, known vulnerabilities, and disallowed license classifications | blocks merge |
| Container image scan | Detects high/critical vulnerabilities in deployable images | blocks merge |
| SPDX SBOM | Records resolved production-image components for release review | generated for release review |

The workflow uses immutable application dependency versions and `npm ci`. Before a production release, replace scanner image tags with reviewed image digests and retain SBOM output with the release record.

The web app's `.npmrc` and all web install commands omit optional dependencies. This intentionally excludes Next's optional Sharp/libvips image-processing chain, which is not approved for the 2026 pilot.

Never grant a CI job write permissions, cloud credentials, production database access, or user data. CI tests use synthetic data only.
