# Product delivery backlog

This document is the delivery plan for the Copperas Cove 2026 pilot and the path from that pilot to a reusable, multi-tenant civic-information platform. It is deliberately ordered: an epic is not started simply because it is attractive; it starts when its dependencies and acceptance criteria are met.

## Product outcomes

1. A voter can enter an address and see only the ballot items that reliably apply to them.
2. Every published factual assertion is traceable to evidence and editorial verification.
3. The service does not retain voter addresses or other unnecessary PII.
4. A city, nonprofit, publisher, or government partner can eventually operate the same product as hosted multi-tenant software or a self-hosted installation.

## Delivery sequence

```text
Foundation and governance
  → Provenance database
    → Authoritative election and boundary data
      → Address-to-ballot resolution
        → Editorial workflows and publication
          → Voter guide and voting logistics
            → Launch operations
              → Post-election and multi-tenant expansion
```

The 2026 pilot stops at the launch-operations epic. The expansion epic is intentionally deferred.

---

## Epic 0 — Foundation, governance, and operational safety

**Goal:** make trust, portability, API documentation, and license compliance default engineering behavior.

### Stories

- As a maintainer, I can boot the web, API, database, and cache locally with one documented command.
- As an operator, I can deploy the same images to a single server or a standard Kubernetes cluster.
- As a reviewer, I can reject an unapproved dependency, provider, or data source before it reaches production.
- As a voter, I can use address resolution without my address being retained.

### Tasks

- [x] Create portable Compose and Kubernetes configuration.
- [x] Publish versioned OpenAPI, Swagger UI, and ReDoc.
- [x] Establish PII, license, source, and API standards.
- [x] Add direct-dependency approval checking.
- [x] Add secret, dependency-vulnerability, container-image, and license/SBOM scans to CI.
- [x] Add deployment-specific secret-management instructions and backup/restore runbook.
- [x] Add accessibility, incident-response, and correction-policy runbooks.

### Exit criteria

- [x] A clean environment can boot the documented stack. (Verified with Docker Compose on 2026-08-20: web and API health endpoints returned HTTP 200.)
- [ ] CI runs tests and policy checks on every change. (Workflow is present; enable it only after runner-cost approval.)
- [x] No approved external service is required for the current scaffold to function.

---

## Epic 1 — Provenance-first PostgreSQL migration layer

**Goal:** establish the durable schema and migration process before editorial data exists.

### Stories

- As an editor, I can publish a claim only with linked source evidence and a verification state.
- As a reviewer, I can see who verified or corrected a record, what changed, and when.
- As a developer, I can apply, roll forward, and test database migrations reproducibly.
- As an operator, I can run a single-tenant database today without blocking later organization/publication isolation.

### Tasks

- [x] Approve and record the licenses for the PostgreSQL driver, SQLAlchemy, Alembic, and test tooling.
- [x] Add the database driver, ORM/data-access layer, migration tool, and pinned lockfiles. (Hash-locked API and migration images rebuilt successfully on 2026-08-20.)
- [x] Add database configuration, health/readiness checks, and a migration command/container target.
- [x] Create migration `001_provenance_core` for organizations/publications, documents, source claims, verification events, elections, ballot versions, ballot items, races/offices, candidates, and propositions.
- [x] Add PostgreSQL enums/check constraints for claim type, editorial status, source type, verification action, and ballot publication status.
- [x] Add immutable revision/audit rules: published records are superseded, never silently overwritten.
- [x] Add tenant/publication indexes and foreign-key constraints.
- [x] Add migration upgrade, fresh-database, rollback/forward-only, and integrity tests. (Verified in CI on 2026-08-20.)
- [x] Document the schema and generate an ER diagram from the migration.

### Exit criteria

- [x] A new database reaches the current schema with one migration command. (Verified with Compose on 2026-08-20.)
- [x] A claim cannot be published without source evidence. (Verified by the PostgreSQL integration test in CI on 2026-08-20.)
- [x] A published record change creates an auditable revision/verification event. (Verified by the PostgreSQL integration test in CI on 2026-08-20.)
- [x] The schema supports one organization now and multiple publications later without a breaking migration.

---

## Epic 2 — Election authorities, sources, and official document ingestion

**Goal:** establish a defensible record of election authorities and source documents before building voter-facing content.

### Stories

- As a researcher, I can register an election authority and all its official source links.
- As an editor, I can see the original document, retrieval metadata, and page citation for every ballot fact.
- As an operator, I can identify stale documents and schedule re-verification.

### Tasks

- [x] Load Copperas Cove, Coryell/Bell/Lampasas County, CCISD, Texas, and applicable special-district authority records. The six confirmed authorities are loaded. The authority-scope audit found no special-purpose body with official 2026 voter-election evidence, so none was invented; see `PILOT_AUTHORITY_SCOPE_AUDIT.md` for recheck triggers.
- [x] Create the source registry and provider/data-license approval workflow. The six pilot sources have dated research records in `PILOT_SOURCE_REVIEW.md`; initial launch permits direct links and manual checks only, while content rights remain pending.
- [x] Add object storage abstraction and checksum-based document records.
- [x] Add manual document upload/retrieval metadata flow before automation.
- [x] Add document page references and source-citation UI primitives.
- [x] Complete verification cadence and stale-source alerts for active elections. The policy, monitoring classes, check history, review/check operator commands, and hybrid alert lifecycle were successfully migrated through `008_source_use_scope` on 2026-08-20; the Copperas Cove registry was loaded with its direct-link/manual-check launch policy. The authenticated dashboard and notification delivery are explicitly deferred to Epic 4, and no monitoring adapter is enabled.

### Decision checkpoint

- [ ] Define the minimum evidence required to create a provisional candidate record. Confirm that “provisional” means source-backed but not independently verified, never unsourced.

### Exit criteria

- Every pilot election/race source links to a retained or reproducibly retrievable official document.
- An editor can identify the exact source and page supporting a ballot item.

---

## Epic 3 — Jurisdiction boundaries and authoritative ballot resolution

**Goal:** return an exact ballot or an explicit unresolved result without retaining the submitted address.

### Stories

- As a voter, I receive the ballot style that applies to my location, not a generic city or ZIP-code ballot.
- As a voter who does not want to enter an address, I can browse and choose among ballots available by ZIP code, city, or county without the product claiming an exact match.
- As a researcher, I can import, version, and reconcile official precinct and district boundaries.
- As a voter whose address cannot be resolved to one ballot, I can compare the plausible ballots with an explanation of which geography and source supports each one.
- As an operator, I can see why a resolution used a particular boundary and ballot version without retaining the voter address.

### Tasks

- [x] Evaluate and approve a geocoder adapter; verify address retention, cost, rate limits, and terms. The Census adapter is approved for opt-in, ephemeral server-side pilot use and remains disabled by default; see `GEOCODER_APPROVAL.md`.
- [x] Add PostGIS and migration support for versioned geometries. Migration `009_boundary_foundations` and PostGIS 3.6 were verified in Compose on 2026-08-20.
- [ ] Import official county, precinct, municipal, school-district, legislative, and special-district boundaries. A checksum-pinned, retained-artifact, draft-only Shapefile importer and publisher/subject provenance split are implemented; real pilot imports remain held for exact source metadata and local-authority confirmation.
- [x] Implement self-owned point-in-polygon jurisdiction resolution. The request-scoped PostGIS resolver uses only active areas and effective verified boundary versions, detects exact edges and overlapping-source conflicts, and returns no coordinates; ballot-style mapping remains separate.
- [ ] Define and implement confidence, ambiguity, source-conflict, and not-found result models. Public API schemas, reason codes, validation, and Swagger routes are implemented; resolver behavior awaits geocoder/boundary integration.
- [ ] Implement non-personalized ballot browsing by ZIP code, city, and county; label results as selectable area matches rather than exact voter matches. API contract is implemented; data lookup and web presentation remain.
- [ ] For unresolved addresses, return and display the evidence-backed plausible ballot set with geographic explanations, source citations, and no preselected winner. Validated API response model is implemented; resolver and web presentation remain.
- [x] Match resolved jurisdiction memberships to verified official ballot styles/versions. Ballot versions now carry an immutable, source-backed combination of geographic requirements; all requirements must match, and zero/multiple results never choose a winner.
- [x] Create synthetic address and boundary-edge test fixtures; never use real voter data. Geocoder, boundary importer, exact-edge, overlap-conflict, and no-match cases use invented examples only.
- [ ] Add daily verification of current ballot versions during the active election period.

### Decision checkpoints

- [x] Hold a boundary-source go/no-go review before importing non-authoritative, incomplete, or conflicting geometry data. Inventory and holds are recorded in `BOUNDARY_SOURCE_REVIEW.md`; private reference imports are approved, while authoritative resolver use still requires authority confirmation.
- [ ] Decide whether unresolved results may emit a privacy-preserving coarse-area signal. If so, specify granularity, aggregation threshold, retention, access controls, and a prohibition on raw address or coordinate retention.

### Exit criteria

- Address resolution never silently falls back to ZIP code; ZIP is available only through a clearly labeled user-selected browse mode.
- A result identifies its ballot version and source evidence, or returns a documented non-confident status.
- An unresolved result may display plausible ballots for comparison but never labels one as the voter's ballot.
- No raw address is stored in databases, queues, analytics, application logs, or support workflows.

---

## Epic 4 — Editorial research and verification workspace

**Goal:** enable a small research team to produce fair, source-backed ballot information efficiently.

### Stories

- As a researcher, I can create a candidate, attach sources, record outreach, and see what information is missing.
- As a verifier, I can independently compare each ballot item against the official document before publication.
- As a candidate, I can submit a standardized response and request a factual correction without controlling editorial treatment.
- As an editor, I can distinguish candidate-provided statements from independently verified facts.

### Tasks

- [ ] Build authenticated editorial roles: researcher, verifier, editor, publisher, administrator.
- [ ] Build candidate, office, race, proposition, and questionnaire editorial forms on top of the provenance schema.
- [ ] Add candidate outreach templates, deadlines, reminders, and immutable communication log.
- [ ] Add research-task queues driven by missing evidence, verification state, election urgency, and overdue-source alerts; make the editorial dashboard the default alert destination.
- [ ] Add editor-controlled, opt-in email preferences for alerts they are authorized to view; keep any ticketing adapter disabled until a provider and disclosure review are approved.
- [ ] Add two-person ballot verification workflow and publication gate.
- [ ] Add candidate correction requests and public correction-log workflow.
- [ ] Add manual import tools for ballot PDF text/OCR drafts; require human verification before publication.

### Decision checkpoints

- [ ] Decide and document how two-person verification is enforced. Before publication features ship, introduce authenticated editorial identities and require two distinct reviewers, neither of whom authored the claim; decide whether this is enforced by PostgreSQL, the workflow service, or both.
- [ ] Decide how polymorphic claim/event subjects are validated before editorial forms can write them. Confirm whether a database trigger, a constrained application service with integrity tests, or a hybrid is required to ensure each `subject_id`/`target_id` exists for its declared type.

### Exit criteria

- No ballot item can publish without the required independent verification.
- Candidate-provided content is visibly labeled and never silently converted into an independently verified fact.
- Every incomplete profile communicates what is missing and when it was last checked.

---

## Epic 5 — Public voter guide and reusable civic API

**Goal:** make verified information understandable and available to both voters and permitted API consumers.

### Stories

- As a voter, I can enter an address and view a readable, sourced ballot organized by level of government.
- As a voter, I can understand an office, a proposition, and a candidate without being told how to vote.
- As an API consumer, I can retrieve published civic data through a stable, documented, rate-limited API.
- As a voter, I can report a missing source or factual correction without submitting my home address.

### Tasks

- [ ] Build ballot-result pages and links to race, office, candidate, and proposition pages.
- [ ] Build source panels, “last verified” displays, and information-missing states.
- [ ] Build neutral office explainers and proposition templates with official wording and sourced financial impact.
- [ ] Build public read API endpoints and OpenAPI examples from the published data model.
- [ ] Add API pagination, rate limiting, caching, observability, and terms of use.
- [ ] Add accessible responsive design, keyboard navigation, plain-language review, and Spanish-content plan.
- [ ] Add correction/report form that does not collect a voter address.

### Decision checkpoints

- [ ] Define privacy-safe measurement methods and event definitions for Ballot Completion Rate, Information Completeness, Source Coverage, and Candidate Participation. Do not introduce address retention, cross-site tracking, or person-level voter analytics.
- [ ] Decide the Spanish-content default, minimum launch coverage, translation review process, and how missing translations are presented.
- [ ] Confirm that commercial/partner API access remains limited to contract design and licensed published data until the post-election expansion epic.

### Exit criteria

- A voter can complete the core address-to-ballot journey on mobile and desktop.
- Every displayed factual claim has a source path.
- Public endpoints expose only published, appropriately licensed data.

---

## Epic 6 — Voting logistics and election operations

**Goal:** make the guide dependable during early voting and Election Day.

### Stories

- As a voter, I can find current official registration, early-voting, Election-Day, identification, and mail-voting information.
- As an operator, I can quickly identify changes in ballot, polling, or logistics sources.
- As an editor, I can publish corrections rapidly with an auditable record.

### Tasks

- [ ] Register and verify official voting-logistics sources by jurisdiction.
- [ ] Build logistics pages with effective dates, source links, and last-verified timestamps.
- [ ] Define election-mode change control, verification cadence, on-call responsibility, and correction SLA.
- [ ] Add uptime, error-rate, resolution-confidence, and stale-source monitoring.
- [ ] Run a pre-launch content, security, accessibility, performance, and disaster-recovery review.
- [ ] Switch to election mode: multiple daily source checks and expedited correction workflow.

### Decision checkpoint

- [ ] Approve the product-success metric dashboard, privacy review, aggregation thresholds, and launch baseline before public beta.

### Exit criteria

- Published logistics are current, dated, and sourced.
- The team can detect source failures and rollback/correct a public data error quickly.
- Launch readiness is approved by product, editorial, and technical owners.

---

## Epic 7 — Post-election retention and platform expansion

**Goal:** preserve useful public history while safely expanding beyond the pilot.

### Stories

- As a voter, I can view historical election information and clearly distinguish unofficial from certified results.
- As a tenant administrator, I can operate a branded publication with isolated editorial access.
- As a partner, I can access licensed, documented data without receiving private data.

### Tasks

- [ ] Archive and preserve election/ballot versions, source documents, corrections, and certification status.
- [ ] Add official-results ingestion and historical results presentation.
- [ ] Add multi-tenant roles, database row-level security, branding, and publication configuration.
- [ ] Build self-hosted installer, upgrade/migration, backup, and support documentation.
- [ ] Add partner API keys, contractual licensing controls, quota enforcement, and usage reporting.
- [ ] Evaluate journalism/government-record ingestion only after editorial and provenance controls are proven.

### Exit criteria

- Historical information remains sourced and distinguishes its election/date/status.
- A second deployment can be hosted or self-hosted without forking the application or compromising tenant isolation.

---

## Priority now

Epics 0–2 are complete for the direct-link/manual-check initial-launch policy. **Epic 3 is active**: its PostGIS/versioned-boundary foundation, optional ephemeral geocoder, controlled draft importer, and self-owned jurisdiction resolver are implemented; real boundary imports and ballot-style membership remain open.
