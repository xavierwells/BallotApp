# Epic 2 handoff — 2026-08-20

## Current state

Epic 2 has its data and operator foundations. Docker Compose successfully
applied the complete migration chain through `008_source_use_scope` on
2026-08-20.

Implemented:

- A multi-tenant authority/source registry with pending-review, approval, and
  retirement lifecycle fields.
- A Copperas Cove pilot manifest and repeat-safe bootstrap command. The
  initial list covers the City, Coryell/Bell/Lampasas counties, CCISD, and the
  Texas Secretary of State. It does not invent special districts.
- Private content-addressed document retention with SHA-256 verification.
  Documents default to public `metadata_only`; a visible copy requires
  explicitly approved rights.
- Manual, operator-only document intake. It stores a supplied local artifact
  and metadata but never fetches the source URL.
- A reusable web citation component that exposes the official link and page
  reference without exposing private object storage.
- Adjustable organization, publication, and authority verification cadence.
- Source monitoring classes and the hybrid alert lifecycle: a manual
  `unchanged` check closes an overdue alert; automated no-change checks do
  not; changed/unavailable/terms-changed work remains open for an editor.
- Operator-only commands record immutable manual checks, keep each approved
  source's review schedule current, and idempotently queue overdue work
  without retrieving a remote source.
- An operator-only review command records the terms, license, retention,
  attribution, and redistribution decision required before a source can be
  approved or monitored.
- Research findings for the six pilot sources are recorded in
  `PILOT_SOURCE_REVIEW.md`. All entries remain pending for content rights but
  use `direct_link_manual_check` for the initial launch; no source grants
  content retention, redistribution, or automated-monitoring rights.

## Next operator steps

After future source changes are committed/pulled, apply migrations and verify
the head:

```powershell
docker compose up -d --build --force-recreate
docker compose logs migrate
docker compose exec postgres psql -U ballot -d ballot -c "SELECT version_num FROM alembic_version;"
```

Current verified deployed version: `008_source_use_scope`. The Copperas Cove
bootstrap was also run successfully: six authorities and six pending-review
sources are registered with the direct-link/manual-check launch scope.

Then load the pending-review pilot registry without contacting any external
source:

```powershell
docker compose exec api python -m app.cli.bootstrap_authorities
```

Do not run automated retrieval or promote a source to `approved` until its
terms, retention, redistribution, and monitoring rights have been reviewed.

## Decisions already made

- The authority registry is extensible. A new ballot intake can create a
  draft authority, but cannot create a geographic district from document text.
- All accepted source artifacts are retained privately. If public-display
  rights are unclear, only source metadata and the official link are public.
- Cadence defaults: monthly for references, weekly for active-election
  sources in the final 90 days, and daily only for active-ballot sources after
  official ballot availability.
- Cadence can be overridden at organization, publication, or authority scope.
- The editorial dashboard is the default alert destination; email is opt-in;
  ticketing is a future optional adapter with no provider selected.
- A manual unchanged check resolves an overdue alert automatically. Changed,
  unavailable, and terms-changed results require editorial handling.

## Questions for later

### Required before source approval or automated monitoring

1. Who is authorized to approve a source and its automation/redistribution
   rights before Epic 4 supplies formal editorial roles?
2. Which pilot source URLs have terms that permit automated monitoring,
   private retention, and/or public redistribution? Record the review for
   each registry entry; official ownership alone is not sufficient.
3. Which special districts are in Copperas Cove pilot scope? Add each only
   after an official election order, ballot, or boundary source establishes
   applicability.
4. The initial-launch decision is direct links plus manual checks only. Before
   later enabling private provenance retention or automation, decide whether
   the team should request written permission from each pilot authority.

### Required before editorial candidate records

5. What minimum source evidence creates a provisional candidate record?
   The current proposed rule is source-backed but not independently verified;
   never unsourced.

### Required before Epic 4 dashboard work

6. What editor-facing details should an unresolved investigation alert show,
   beyond source, latest check result, election context, and source URL?
7. How long should resolved source-alert history remain visible in the
   dashboard, and may alerts be reopened after resolution?
8. Which email frequency controls should an editor have: immediate, daily
   digest, weekly digest, or another model?

### Explicitly deferred

9. Which ticketing provider, if any, should be supported first? No ticketing
   integration should be implemented or enabled before this is chosen and its
   data-disclosure rules are reviewed.
