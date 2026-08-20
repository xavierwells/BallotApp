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

- [ ] Approve and record the licenses for the PostgreSQL driver, SQLAlchemy, Alembic, and test tooling.
- [ ] Add the database driver, ORM/data-access layer, migration tool, and pinned lockfiles.
- [ ] Add database configuration, health/readiness checks, and a migration command/container target.
- [ ] Create migration `001_provenance_core` for organizations/publications, documents, source claims, verification events, elections, ballot versions, ballot items, races/offices, candidates, and propositions.
- [ ] Add PostgreSQL enums/check constraints for claim type, editorial status, source type, verification action, and ballot publication status.
- [ ] Add immutable revision/audit rules: published records are superseded, never silently overwritten.
- [ ] Add tenant/publication indexes and foreign-key constraints.
- [ ] Add migration upgrade, fresh-database, rollback/forward-only, and integrity tests.
- [ ] Document the schema and generate an ER diagram from the migration.

### Exit criteria

- A new database reaches the current schema with one migration command.
- A claim cannot be published without source evidence.
- A published record change creates an auditable revision/verification event.
- The schema supports one organization now and multiple publications later without a breaking migration.

---

## Epic 2 — Election authorities, sources, and official document ingestion

**Goal:** establish a defensible record of election authorities and source documents before building voter-facing content.

### Stories

- As a researcher, I can register an election authority and all its official source links.
- As an editor, I can see the original document, retrieval metadata, and page citation for every ballot fact.
- As an operator, I can identify stale documents and schedule re-verification.

### Tasks

- [ ] Create Copperas Cove, Coryell/Bell/Lampasas County, CCISD, Texas, and applicable special-district authority records.
- [ ] Create the source registry and provider/data-license approval workflow.
- [ ] Add object storage abstraction and checksum-based document records.
- [ ] Add manual document upload/retrieval metadata flow before automation.
- [ ] Add document page references and source-citation UI primitives.
- [ ] Add verification cadence and stale-source alerts for active elections.

### Exit criteria

- Every pilot election/race source links to a retained or reproducibly retrievable official document.
- An editor can identify the exact source and page supporting a ballot item.

---

## Epic 3 — Jurisdiction boundaries and authoritative ballot resolution

**Goal:** return an exact ballot or an explicit unresolved result without retaining the submitted address.

### Stories

- As a voter, I receive the ballot style that applies to my location, not a generic city or ZIP-code ballot.
- As a researcher, I can import, version, and reconcile official precinct and district boundaries.
- As a voter near an uncertain boundary, I am told the result is unresolved rather than being shown a guessed ballot.
- As an operator, I can see why a resolution used a particular boundary and ballot version without retaining the voter address.

### Tasks

- [ ] Evaluate and approve a geocoder adapter; verify address retention, cost, rate limits, and terms.
- [ ] Add PostGIS and migration support for versioned geometries.
- [ ] Import official county, precinct, municipal, school-district, legislative, and special-district boundaries.
- [ ] Implement self-owned point-in-polygon jurisdiction resolution.
- [ ] Define and implement confidence, ambiguity, source-conflict, and not-found result models.
- [ ] Match resolved jurisdiction memberships to verified official ballot styles/versions.
- [ ] Create synthetic address and boundary-edge test fixtures; never use real voter data.
- [ ] Add daily verification of current ballot versions during the active election period.

### Exit criteria

- Resolution never falls back to ZIP code.
- A result identifies its ballot version and source evidence, or returns a documented non-confident status.
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
- [ ] Add research-task queues driven by missing evidence, verification state, and election urgency.
- [ ] Add two-person ballot verification workflow and publication gate.
- [ ] Add candidate correction requests and public correction-log workflow.
- [ ] Add manual import tools for ballot PDF text/OCR drafts; require human verification before publication.

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

The active work is **Epic 1**. Its first task is to approve the persistence/migration dependencies, then implement and test `001_provenance_core`. No candidate profile, proposition, or ballot-writing feature should begin before that migration passes its exit criteria.
