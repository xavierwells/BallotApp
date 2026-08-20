# Operations runbook

This runbook applies to the pilot and must be updated before the first production deployment.

## Secrets

- Do not commit `.env`, database passwords, API keys, signing keys, or service-account files.
- Local development uses an uncommitted `.env` copied from `.env.example`.
- A single Docker host keeps secrets in root-owned files outside the checkout or in the host's protected secret store; pass only the required values to Compose at runtime.
- Kubernetes uses `Secret` objects or an approved external secret manager. Do not put secrets in ConfigMaps, manifests, logs, OpenAPI examples, or CI variables printed to output.
- Rotate a secret immediately when it is committed, appears in logs, or is exposed to an unauthorized party. Create a verification event and incident record; never paste the secret into the record.

## PostgreSQL backup and restore

The pilot database must have a daily encrypted logical backup and a tested restore at least monthly. Retention, storage location, encryption keys, RPO, and RTO require an operations-owner decision before production.

Example logical backup from a Compose host:

```sh
docker compose exec -T postgres pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc > ballot-YYYY-MM-DD.dump
```

Restore only into an empty, isolated target database after confirming the target name and environment:

```sh
docker compose exec -T postgres createdb -U "$POSTGRES_USER" ballot_restore_test
docker compose exec -T postgres pg_restore -U "$POSTGRES_USER" -d ballot_restore_test --clean --if-exists < ballot-YYYY-MM-DD.dump
```

Do not use production addresses or credentials in a restore test. Record the restore date, operator, duration, schema version, and result.

## Incident response

| Severity | Example | Initial response |
| --- | --- | --- |
| SEV-1 | Confirmed PII disclosure, broad false ballot publication, database loss | stop affected publication/endpoint, preserve evidence, notify incident owner immediately |
| SEV-2 | Incorrect race/proposition or voting-logistics information with limited reach | correct or unpublish, verify source, publish correction note |
| SEV-3 | Broken page, stale non-critical content, failed background job | create issue, schedule fix, monitor |

For every SEV-1 or SEV-2: record detection time, scope, source of truth, containment, correction, user-facing notice, and prevention action. Never place raw addresses, credentials, or voter data in incident records.

## Editorial correction process

1. Receive a correction through the public form, authoritative source, candidate, or internal review.
2. Classify it as ballot-critical, factual, attribution, or presentation-only.
3. For ballot-critical issues, unpublish the affected item if confidence is insufficient; do not leave an uncertain item visible.
4. Verify against the primary authority/source and obtain a second reviewer for ballot changes.
5. Publish a superseding record and public correction note with date, scope, and evidence. Do not silently overwrite published data.
6. Log the editorial decision and close only after the public page, API, caches, and related views agree.
