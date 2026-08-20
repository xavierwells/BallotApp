# Epic 3 boundary foundations

Migrations `009_boundary_foundations` and `010_boundary_source_roles` supply the storage layer for official,
versioned geographic boundaries. It does **not** approve a geocoder, import a
real boundary dataset, or decide how an ambiguous location maps to a ballot.
Those remain separate Epic 3 decisions.

The controlled draft importer is documented in [BOUNDARY_IMPORT.md](BOUNDARY_IMPORT.md).

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
  review decision, reviewer, publisher authority, and subject authority. The
  two authorities may differ when a state body publishes county geometry.
- `boundary_versions` stores normalized `MultiPolygon` geometry in WGS 84
  (`SRID 4326`), its SHA-256 checksum, effective period, review evidence, and
  optional predecessor.
- `ballot_geographic_requirements` records the source-backed combination of
  areas required for a ballot version. Requirements become immutable when the
  ballot is published.
- Composite foreign keys require an area and boundary version to belong to the
  dataset's subject authority, while separately requiring the source registry
  entry to belong to the dataset's publisher. Both authorities remain inside
  the same publication boundary.
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

The boundary-source review now permits private reference imports with retained
provenance. TLC's 2026-primary precinct source is pinned in a repeatable pilot
manifest, but it remains draft/reference geometry and is not eligible for the
November resolver until the responsible county confirms applicability or a
superseding general-election source is reviewed. Public source redistribution
remains metadata-only. Automated tests still use invented geometry and no real
voter information.

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
docker run --rm --mount type=bind,source="${PWD}/data",target=/app/data,readonly ballot-api-test
```

Expected migration revision: `013_official_ballot_intake`. If custom
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
