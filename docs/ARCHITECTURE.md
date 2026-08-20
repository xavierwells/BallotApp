# Initial architecture

The platform is a modular monolith with separately deployable web and API processes. This is intentionally not a microservice system: its boundaries are deployable and testable now without creating distributed-system overhead.

```text
Browser
  ├── Web application (Next.js)
  └── Civic API (FastAPI / OpenAPI)
          ├── PostgreSQL + PostGIS (civic and provenance data)
          ├── Valkey (future job queue/cache)
          └── Private document storage (source evidence)
```

## API boundaries

- `/api/v1`: published civic-information API; the public, reusable data boundary.
- `/api/editorial/v1`: future researcher/editor workflow API; authenticated and auditable.
- `/api/partner/v1`: future partner/data-license API; separately rate-limited and authorized.

Swagger UI and OpenAPI are generated directly by the API service. The OpenAPI contract is the source for external integration documentation and future SDK generation.

## Multi-tenant and self-hosted posture

An organization/publication is a tenant boundary; a city is a civic jurisdiction. A single publication can cover multiple cities, and a city can span several election authorities. Tenant fields will be introduced before editorial data exists, but a Copperas Cove deployment can operate with one organization.

The same OCI images run under Compose on a single host or under any conforming Kubernetes distribution, including Rancher-managed clusters and DigitalOcean Kubernetes. Self-hosted installations receive their own database; the hosted offering will use tenant-scoped data and database row-level security.

## Address-resolution boundary

Address resolution is an ephemeral service boundary. It returns ballot applicability, never a stored address. It has two deliberately separate stages:

1. **Geocoding:** address to coordinates. This is the only stage where an approved external provider could receive a raw address.
2. **Jurisdiction resolution:** coordinates to precinct, district, and ballot style. This is a self-owned PostGIS process backed by official boundary data, never a black-box civic-data provider.

The authoritative resolver may only select an approved geocoder adapter after the provider's license, terms, cost, and privacy policy have been reviewed. Read [`ADDRESS_RESOLUTION.md`](ADDRESS_RESOLUTION.md) before implementing either stage.

## Source-document storage

Source artifacts are content-addressed by SHA-256 and retained privately for
provenance. The current `filesystem` backend runs on the same private volume
as a self-hosted API. Its `DocumentStore` contract intentionally has no public
URL operation; a future approved S3-compatible adapter can use DigitalOcean
Spaces or another provider without changing the document model. See
[`SOURCE_REGISTRY.md`](SOURCE_REGISTRY.md) for the separate public-visibility
policy.

## Provenance before profiles

The first persisted editorial feature must use the claim/source/verification model in [`PROVENANCE_SCHEMA.md`](PROVENANCE_SCHEMA.md). Candidate profiles, proposition explainers, and AI-assisted research must not introduce data outside that evidence model.
