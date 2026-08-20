# Epic 3 boundary foundations

Migration `009_boundary_foundations` supplies the storage layer for official,
versioned geographic boundaries. It does **not** approve a geocoder, import a
real boundary dataset, or decide how an ambiguous location maps to a ballot.
Those remain separate Epic 3 decisions.

## What is now represented

```text
election authority
  ├── geographic area (the named county, precinct, district, or municipality)
  └── registered boundary source
        └── boundary dataset review/import
              └── boundary version (effective dates + geometry + checksum)
```

- `geographic_areas` stores stable civic identities independently of changing
  map shapes. Adding a newly evidenced district creates a row; it does not
  require a hard-coded pilot district list.
- `boundary_datasets` records the exact registered source URL, date checked,
  review decision, reviewer, and authority that supplied a future import.
- `boundary_versions` stores normalized `MultiPolygon` geometry in WGS 84
  (`SRID 4326`), its SHA-256 checksum, effective period, review evidence, and
  optional predecessor.
- Composite foreign keys require an area, dataset, and boundary version to
  belong to the same authority. The authority belongs to a publication, which
  preserves the existing tenant boundary.
- A GiST spatial index supports future point-in-polygon queries.
- Imported/rejected dataset reviews and verified/superseded/retired boundary
  versions are immutable. Corrections require a replacement dataset or a
  superseding version.

An unknown effective date is permitted while a boundary is a draft. It must be
known before the boundary can become verified. The database intentionally does
not reject overlapping versions: overlap may be evidence of a source conflict,
and hiding that conflict would be less safe than preserving it for review.

## Privacy boundary

These tables contain public civic geography, not voter input. There is no table
for submitted addresses, geocoder requests, resolved coordinates, or voter
profiles. The later resolution service must keep those values in request memory
only and must not put them in logs, analytics, queues, or support records.

## Pilot source policy

The schema is ready for future imports, but the initial-launch policy remains:
direct links and manual checks only. Do not load real geometry until the
boundary-source go/no-go review confirms authority, completeness, permitted
use, attribution, retention, and redistribution terms. All automated tests use
invented geometry near an invented point; they use no real voter information.

## Verify locally

The existing PostgreSQL 18 volume can remain in place. The PostGIS image uses
the same PostgreSQL 18 volume path, and migration 009 enables the extension in
the existing application database.

```powershell
docker compose pull postgres
docker compose build api migrate
docker compose up -d --force-recreate
docker compose logs migrate
docker compose exec postgres psql -U ballot -d ballot -c "SELECT PostGIS_Version();"
docker compose exec postgres psql -U ballot -d ballot -c "SELECT version_num FROM alembic_version;"
docker build --target test --tag ballot-api-test apps/api
docker run --rm ballot-api-test
```

Expected migration revision: `009_boundary_foundations`. If custom
`POSTGRES_USER` or `POSTGRES_DB` values are set in `.env`, use those in the two
`psql` commands. Tests use the Dockerfile's dedicated `test` target because the
security-hardened production API image intentionally contains neither Pytest
nor Python package-installation tools. The local test command skips the
fresh-database migration integration test; CI runs that test against its
isolated PostGIS service.

## Decisions deliberately deferred

- geocoder provider approval and its privacy/terms review;
- official Copperas Cove-area boundary sources and import permission;
- conflict and boundary-edge thresholds;
- point-in-polygon result contract;
- ZIP/city/county browse indexing and presentation;
- unresolved-result plausible-ballot comparison presentation;
- geographic-area-to-ballot-style membership rules;
- whether unresolved results may emit any coarse-area signal.
