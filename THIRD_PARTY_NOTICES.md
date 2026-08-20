# Third-party notices and approval ledger

Only the components listed below are approved for the initial scaffold. This is not a substitute for a lockfile-level SBOM and license scan in CI.

| Component | Purpose | License | Approval basis |
| --- | --- | --- | --- |
| FastAPI | API framework and OpenAPI/Swagger generation | MIT | [upstream project metadata](https://github.com/fastapi/fastapi/blob/master/pyproject.toml) |
| Alembic | PostgreSQL schema migrations | MIT | [PyPI project metadata](https://pypi.org/project/alembic/) |
| SQLAlchemy | database access and schema metadata | MIT | [PyPI project metadata](https://pypi.org/project/SQLAlchemy/) |
| pg8000 | pure-Python PostgreSQL driver | BSD-3-Clause | [PyPI project metadata](https://pypi.org/project/pg8000/) |
| PyShp | Read retained ESRI Shapefile boundary datasets without native geospatial libraries | MIT | [upstream project and license](https://github.com/GeospatialPython/pyshp) |
| Next.js | web framework | MIT | [upstream package metadata](https://github.com/vercel/next.js/blob/canary/packages/next/package.json) |
| React | UI runtime | MIT | upstream project license |
| PostgreSQL | relational database | PostgreSQL License | [official license](https://www.postgresql.org/about/licence/) |
| PostGIS | Spatial types, indexes, and geographic queries in PostgreSQL | GPL-2.0-or-later | [official license FAQ](https://postgis.net/documentation/faq/gpl-license/); the application communicates with PostGIS as a database service and does not incorporate or modify its code |
| Docker PostGIS image | PostgreSQL 18 + PostGIS 3.6 development/runtime image | MIT (image packaging); bundled components retain their own licenses | [upstream image repository](https://github.com/postgis/docker-postgis) |
| U.S. Census Geocoding Services API | Optional server-side conversion of an ephemeral U.S. address to a temporary coordinate | U.S. government service under custom API terms | [approval record](docs/GEOCODER_APPROVAL.md); disabled by default, address disclosure required, no BallotApp retention |
| Texas Legislative Council boundary datasets | Reference precinct, school-district, and enacted legislative-plan geometry | Creative Commons Attribution as identified on each selected dataset | [Capitol Data Portal](https://data.capitol.texas.gov/); private source retention and transformation approved with attribution, checksums, version pinning, and local-authority confirmation before authoritative use |
| Valkey | optional cache and future queue broker | BSD-3-Clause | [upstream project](https://github.com/valkey-io/valkey) |
| Uvicorn | ASGI server | BSD-3-Clause | upstream project license |
| Pytest | test runner | MIT | upstream project license |
| pip-tools | hash-locked Python dependency generation | BSD-3-Clause | [PyPI project metadata](https://pypi.org/project/pip-tools/) |
| HTTPX | API test-client dependency | BSD-3-Clause | upstream project license |
| TypeScript and DefinitelyTyped packages | compile-time web types | Apache-2.0 / MIT | upstream project licenses |
| pip-audit | Python dependency vulnerability scanner | Apache-2.0 | [upstream project](https://github.com/pypa/pip-audit) |
| Trivy | vulnerability, secret, misconfiguration, license, image, and SBOM scanner | Apache-2.0 | [upstream project](https://github.com/aquasecurity/trivy) |
| GitHub checkout action | CI source checkout | MIT | [upstream project](https://github.com/actions/checkout) |
| GitHub setup-python action | CI's pinned Python runtime | MIT | [upstream project](https://github.com/actions/setup-python) |

## Explicitly excluded dependencies

| Component | Reason | Decision |
| --- | --- | --- |
| Sharp and `@img/sharp-*` / `@img/sharp-libvips-*` | Optional Next.js image-processing chain includes LGPL-3.0-or-later libvips binaries. | Rejected for the 2026 pilot; npm installs omit optional dependencies. Reconsider only through a recorded license exception and image-optimization design review. |

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
