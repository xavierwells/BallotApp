# Boundary import operator guide

The Epic 3 importer is a maintenance command inside the existing API image. It
does not add another service. It accepts only a checksum-pinned HTTPS
Shapefile ZIP from an approved source-registry entry, retains the original ZIP
privately, and creates draft/reference geometry. It cannot mark a dataset
imported or a boundary verified.

## Safety model

- Dry-run validation is the default; database writes require `--apply`.
- Re-running an identical pinned county import is idempotent; a partial or
  duplicate prior import fails closed instead of creating another dataset.
- One retained statewide artifact may support several subject counties. The
  immutable document is reused by checksum; it is never updated to attach the
  next county slice.
- The exact expected SHA-256 is mandatory and a download is limited to 100 MiB.
- The ZIP must contain one polygon `.shp`/`.shx`/`.dbf` component set.
- The source registry must be approved for private retention or public copies.
- The original archive is retained as immutable evidence with metadata-only
  public access.
- A source coordinate-system SRID is explicit; PostGIS normalizes valid polygon
  geometry to WGS 84 (`SRID 4326`). The command never guesses a projection.
- Publisher and subject are separate. For example, a state publisher may
  supply a county boundary without being represented as the county authority.
- A human still must compare the result with the responsible local authority
  before any later publication/verification step.

## Workflow

1. Record the publisher and direct dataset endpoint in the authority source
   registry, including its license/terms decision and approved retention use.
2. Record the exact download URL, dataset release/effective date, source SRID,
   relevant field names, filter, attribution, and SHA-256 in the import review.
3. Run without `--apply`; inspect the reported feature count.
4. Run the same command with `--apply`; this creates only draft records.
5. Inspect the imported shapes and compare them with the subject authority's
   current official material. Review/promotion is a separate future command.

Use `python -m app.cli.import_boundaries --help` inside the API image for all
arguments. Example placeholders deliberately cannot be copied as a real import:

```powershell
docker compose run --rm api python -m app.cli.import_boundaries `
  --publisher-slug PUBLISHER --subject-slug COUNTY --source-slug DATASET `
  --source-url https://example.invalid/pinned.zip --sha256 64_HEX_CHARACTERS `
  --title "Dataset release" --publisher-name "Publisher" `
  --area-type voting_precinct --source-srid EPSG_NUMBER `
  --identifier-field PRECINCT --name-field LABEL `
  --filter-field COUNTY --filter-value COUNTY_NAME
```

## Copperas Cove pilot reference manifest

The repository pins TLC's 2026-primary precinct artifact and its three pilot
county slices in
`data/boundaries/copperas-cove-2026-primary-reference.json`. This is reference
geometry, not proof of November 2026 applicability.

First synchronize the registry, then record the documented CC
Attribution/private-retention review. Use an operator identifier for
`--reviewer-reference`; do not enter voter data.

```powershell
docker compose run --rm api python -m app.cli.bootstrap_authorities
docker compose run --rm api python -m app.cli.review_source `
  --organization-slug whats-on-my-ballot `
  --publication-slug copperas-cove `
  --authority-slug texas-legislative-council `
  --source-slug precincts-2026-primary `
  --approval-status approved `
  --permitted-use private_retention `
  --reviewer-reference YOUR-OPERATOR-ID `
  --terms-url https://data.capitol.texas.gov/dataset/precincts `
  --source-license "Creative Commons Attribution" `
  --cost-model free `
  --rate-limit "manual pinned download only" `
  --retention-rule "retain privately for provenance; do not redistribute the original ZIP" `
  --attribution-requirement "Texas Legislative Council; link the dataset page" `
  --redistribution-rights metadata_only `
  --review-notes "2026 primary reference only; county confirmation required for November resolver use"
```

Validate the checksum, shapefile schema, and expected county feature counts
without writing to the database:

```powershell
docker compose run --rm api python -m app.cli.import_boundary_manifest `
  --manifest /app/data/boundaries/copperas-cove-2026-primary-reference.json
```

Only after validation succeeds, add `--apply`. The resulting geographic areas
and boundary versions are always `draft`; the manifest loader rejects any
manifest that claims verified eligibility.
