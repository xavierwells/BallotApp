# Boundary import operator guide

The Epic 3 importer is a maintenance command inside the existing API image. It
does not add another service. It accepts only a checksum-pinned HTTPS
Shapefile ZIP from an approved source-registry entry, retains the original ZIP
privately, and creates draft/reference geometry. It cannot mark a dataset
imported or a boundary verified.

## Safety model

- Dry-run validation is the default; database writes require `--apply`.
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
