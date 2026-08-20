# Deployment

## Local development

Copy `.env.example` to `.env`, choose a strong local database password, then:

```sh
docker compose up --build
```

The stack exposes only the web (`3000`) and API (`8080`) ports. PostgreSQL and Valkey remain private to the Docker network.
Compose applies the forward-only schema migration before starting the API. To apply it explicitly, run `docker compose run --rm migrate` (or `make db-upgrade`).

## Single server / bare metal

Install Docker Engine and the Compose plugin on a supported Linux host. Supply production values through the host's protected environment or a secrets manager, then run:

```sh
docker compose -f compose.yaml -f compose.production.yaml up -d --build
```

Place a TLS-terminating reverse proxy in front of the `web` and `api` services. Back up the `postgres_data` volume, test restores, and send logs to a managed destination that redacts request bodies. For production, replace the local Postgres service with a managed PostgreSQL service or a separately operated, backed-up database host.

## Rancher and DigitalOcean Kubernetes

Rancher manages standard Kubernetes resources; it does not require a Rancher-specific application runtime. Build and push the `web` and `api` images to a registry, replace placeholder image references in `infra/kubernetes/kustomization.yaml`, create database credentials as a Kubernetes Secret, and apply the manifests through Rancher or `kubectl`.

The manifests intentionally omit Postgres and Valkey. Use managed services or separately administered StatefulSets in Kubernetes; election data is not suitable for an unbacked ephemeral database. Build the web image with `NEXT_PUBLIC_API_BASE_URL=/api` so browser requests stay on the public origin.

Use the same OCI images for Rancher, DigitalOcean Kubernetes, and a bare-metal Docker host. Deployment is an environment concern, not an application fork.
