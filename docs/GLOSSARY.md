# BallotApp glossary

This is the plain-language reference for civic, election, editorial, product,
data, and software terms used throughout BallotApp. Definitions describe how
the project uses a term; election law or an authority's own terminology may be
more specific.

## How the main concepts connect

```text
Entered address (discarded)
  -> temporary map coordinate
  -> official boundary versions
  -> applicable jurisdictions and districts
  -> authoritative ballot style
  -> ballot version
  -> races, candidates, and propositions
  -> sourced claims and citations shown to the voter
```

A separate trust chain explains where displayed information came from:

```text
Election authority
  -> registered official source link
  -> source document or manually observed fact
  -> editorial verification
  -> published claim and visible citation
```

## Commonly confused civic terms

| Term | Plain-language meaning | BallotApp usage |
| --- | --- | --- |
| **Authority** | A body responsible for administering an election or officially publishing election information. | The City of Copperas Cove, a county elections office, CCISD, and the Texas Secretary of State are authorities. An authority is not automatically a geographic district. |
| **Jurisdiction** | The geographic area or subject matter over which a government body has legal responsibility. | Used to decide which governments and elections may apply to a voter. A city, county, school district, and special district may overlap. |
| **District** | A defined geographic area used for representation, services, taxation, or elections. | A district must come from official boundary evidence. Seeing a district name in a document is not enough to create its boundary. |
| **Precinct** | A small election-administration area created by a county. | Precincts help organize voters, polling locations, and ballot styles. A precinct is not the same thing as a city-council or school-board district. |
| **Ballot style** | The exact combination of contests presented to a particular group of voters. | This is the authoritative bridge between geographic memberships and the ballot a voter should receive. Two nearby addresses can have different styles. |
| **Political subdivision** | A local governmental unit created under state law, such as a city, school district, or water district. “Political” here means governmental, not partisan. | A broad category used when reviewing possible election authorities. It does not mean the body supports a political party. |
| **Special district** | A government body created for a limited purpose or service area, such as water, hospital, utility, or community-college services. | Added only when official evidence shows both applicable geography and a relevant voter election. |
| **Municipality** | An incorporated city or town with its own local government. | The City of Copperas Cove is the pilot municipality. |
| **County** | A regional unit of state government that commonly administers elections and voter registration. | Copperas Cove crosses county boundaries, so Coryell, Bell, and Lampasas County sources may matter. |
| **Independent school district (ISD)** | A local public-school system with its own governing board and geographic boundaries. | Copperas Cove ISD is an election authority separate from the City. “Independent” does not mean private. |
| **Appraisal district / CAD** | A county-level body that determines taxable property values for participating taxing units. | Its governance may involve appointment or entity voting rather than a direct public ballot, so it is not assumed to be a voter contest. |
| **Groundwater conservation district (GCD)** | A special-purpose body that manages groundwater within an official service area. | It matters only if official boundary and election evidence show that its contest applies to pilot voters. |
| **Secretary of State (SOS)** | The Texas state office that serves as the state's chief election authority and publishes statewide guidance. | A state-level authority and reference source; not the administrator of every local contest. |
| **Governing body** | The group legally responsible for making decisions for a government entity. | Examples include a city council, school board, commissioners court, or district board. |
| **City council place** | A numbered seat on a city council. | “Place 6” is a seat, not necessarily a geographic district. Whether places are at-large or district-based must be verified. |
| **At-large seat** | A seat elected by all eligible voters in the entity rather than voters in one subdistrict. | Stored only after an official source confirms the election method. |
| **Single-member district** | A geographic district that elects one representative. | Requires an official, versioned boundary before address resolution can use it. |
| **Incumbent** | The person currently holding an office. | A sourced candidate attribute, not an endorsement or prediction. |
| **Term of office** | The period for which someone is elected or appointed to serve. | Descriptive office information that requires a source. |
| **Nonpartisan race** | A contest in which party labels do not appear on the ballot under the governing election rules. | “Nonpartisan” does not mean candidates have no personal political views. |

## Election and ballot terms

| Term | Plain-language meaning | BallotApp usage |
| --- | --- | --- |
| **Election** | A legally defined event on a particular date in which voters choose candidates or decide measures. | A structured record tied to its authority, jurisdiction, date, type, and official evidence. |
| **General election** | A regularly scheduled election for offices or measures. | The label is taken from the authority; it does not necessarily mean only federal or statewide races. |
| **Primary election** | An election used by a political party to choose nominees for a later election. | Kept distinct from the later general election. |
| **Special election** | An election called outside the ordinary cycle or for a specific vacancy or measure. | Requires an official order or notice; “special” does not describe importance. |
| **Runoff election** | A later election held when no candidate met the rule required to win the first contest. | A separate election event with its own date and ballot evidence. |
| **Joint election** | One administered election that includes contests from multiple political subdivisions. | The county may administer it, but each participating body remains the authority for its own contest. |
| **Election order** | Formal action by a governing body calling an election. | Strong evidence that an election exists, but not always the final source for candidates or ballot order. |
| **Notice of election** | The required public notice stating details such as date, locations, hours, or participating entities. | An official source for logistics and scope, subject to later updates. |
| **Candidate-filing notice** | A notice stating which offices are open and when candidates may file. | Evidence that an office is expected on the election, not proof of the final candidate list. |
| **Filing deadline** | The last time a candidate may submit an application for a place on the ballot. | Used to distinguish provisional candidate research from a final ballot list. |
| **Candidate** | A person officially seeking election to a particular office in a particular race. | A person is not treated as a confirmed candidate without source-backed evidence for that race. |
| **Office** | The public position being filled, such as mayor, council member, trustee, or judge. | Reusable description of the role, level of government, jurisdiction, and term. |
| **Seat / place** | One position within a multi-member governing body. | Modeled separately when an authority numbers or otherwise distinguishes positions. |
| **Race / contest** | The ballot choice used to fill an office. | Connects an election, office, candidates, ballot title, and number of available seats. |
| **Proposition / measure** | A question voters decide directly rather than an office filled by a candidate. | Stores official wording and a sourced plain-language explanation. “For” and “against” arguments must remain clearly attributed. |
| **Ballot item** | One ordered race or proposition on a ballot. | Preserves the sequence and page citation from an official ballot version. |
| **Ballot version** | One immutable edition of an official ballot or ballot style. | If the authority changes a ballot, BallotApp creates a new version rather than overwriting history. |
| **Official ballot** | The authority's finalized ballot used for the election. | Stronger evidence than a filing notice, candidate packet, or draft list. |
| **Sample ballot** | A public example of what a ballot will look like. | Useful evidence, but the project verifies that it represents the correct ballot style and version. |
| **Canvass** | The official process of reviewing and accepting election results. | A canvass record is stronger than unofficial election-night totals. |
| **Certification** | The formal declaration that results or another election fact are official. | Stored with its authority, date, and source. |
| **Polling place** | A location where assigned voters cast ballots. | May be precinct-specific. |
| **Vote center** | A polling location that eligible county voters may use regardless of assigned precinct, when county rules allow it. | Must be confirmed for the specific election; it is not assumed from a prior election. |
| **Early voting** | In-person voting during the authorized period before Election Day. | Dates, hours, and locations are time-sensitive logistics facts. |
| **Ballot by mail** | A voting method in which an eligible voter receives and returns a ballot through authorized mail procedures. | BallotApp links to official eligibility and deadline guidance rather than deciding eligibility. |
| **Voting logistics** | Practical information needed to vote: dates, hours, locations, identification rules, accessibility, and mail-ballot instructions. | Treated as rapidly changing, high-importance sourced content. |

## Geography and privacy terms

| Term | Plain-language meaning | BallotApp usage |
| --- | --- | --- |
| **Geocoding** | Converting a street address into map coordinates. | A temporary request step. The raw address and resulting precise location are not stored as a voter profile. |
| **Jurisdiction resolution** | Determining which official geographic areas contain a coordinate. | Performed against versioned official boundaries to produce district memberships and a ballot style. |
| **Boundary dataset** | A digital map describing the edge of a jurisdiction, precinct, or district. | Must have an authority, effective dates, source, checksum, and version. |
| **Point-in-polygon** | A map calculation that asks which boundary shape contains a coordinate. | The core geometry operation used after geocoding. It is not sufficient by itself when official sources conflict. |
| **Boundary ambiguity** | A case where an address is near an edge, data is missing, or sources disagree. | Returns an explicit unresolved state; the system must not guess. |
| **Resolution confidence** | A structured indication of how strongly the available evidence supports a geographic match. | Low confidence leads to review or an unresolved response, not a fabricated ballot. |
| **Ballot browse mode** | A way to inspect ballots without entering a residential address. | The voter selects a ZIP code, city, or county and then chooses from overlapping ballots. Results are not presented as an exact personal match. |
| **Plausible ballot set** | The ballots that available boundary and source evidence indicate could apply when one exact result cannot be established. | Shown with geographic explanations and citations; no ballot is preselected or described as resolved. |
| **PII (personally identifiable information)** | Information that can identify or closely locate a person, such as a full residential address. | Entered addresses must not be stored in the database, logs, analytics, queues, URLs, or support tools. |
| **Data minimization** | Collecting and retaining only what the product genuinely needs. | BallotApp returns a ballot result identifier and discards request-scoped address data. |

## Sources, evidence, and editorial terms

| Term | Plain-language meaning | BallotApp usage |
| --- | --- | --- |
| **Provenance** | The record of where information came from and what happened to it. | Includes authority, URL, document, retrieval/check time, checksum, page citation, verifier, and change history. |
| **Official source** | A source published by the body responsible for the information. | Preferred for election facts, but official status alone does not grant copying or automation rights. |
| **Primary source** | Original evidence produced by the responsible person or body. | Examples include an election order, official ballot, filing, or candidate response. |
| **Secondary source** | Reporting or analysis based on primary material. | May add context but generally does not replace official evidence for ballot facts. |
| **Source registry** | The controlled list of official URLs and their review status. | Records ownership, purpose, terms, permitted use, monitoring class, and review history. Registering a URL is not blanket approval. |
| **Source registry entry** | One reviewed or pending URL belonging to one authority. | URLs are retired and replaced rather than silently repurposed. |
| **Document / artifact** | A particular file or captured source item retained as evidence. | Immutable and checksum-addressed when retention rights permit storage. Under the initial-launch policy, pilot sources are direct-link/manual-check only. |
| **Metadata** | Descriptive facts about something rather than its full content. | Examples include title, official URL, publisher, retrieval date, checksum, and page number. |
| **Citation** | The visible reference that lets a reader inspect the supporting source. | Shows the authority, direct official link, date checked/retrieved, and page reference when available. |
| **Source claim / claim** | One factual assertion or attributed statement supported by evidence. | Keeps verified facts, candidate statements, analysis, and community tips from being mixed together. |
| **Verified fact** | A factual claim checked against sufficient authoritative evidence. | Requires a source and verification history; it is not merely text that sounds factual. |
| **Candidate statement** | A claim expressing what a candidate said, promised, or submitted. | Attributed to the candidate and not presented as independently proven fact. |
| **Editorial analysis** | An explanation or interpretation produced by the project. | Visibly distinct from official wording and attributed statements. |
| **Community tip** | Information submitted for possible research. | A lead only; never publication-ready evidence by itself. |
| **Editorial status** | The stage of content in the research and publication process. | Typical states are draft, needs review, verified, published, retracted, or superseded. |
| **Verification check** | A recorded review of whether a source is unchanged, changed, unavailable, or governed by changed terms. | Manual for the initial launch. It updates the next check deadline and retains immutable history. |
| **Verification event** | An audit record showing who created, verified, published, corrected, retracted, or superseded content. | Broader than a source availability check and tied to editorial actions. |
| **Cadence** | How often a source should be checked. | Defaults may be monthly, weekly near an election, or daily for an official ballot; policies can be overridden by tenant, publication, or authority. |
| **Stale / overdue source** | A source whose scheduled check time has passed. | Means “needs review,” not “known to be wrong.” |
| **Monitoring class** | A category controlling how urgently a source is checked. | Current classes are active ballot, active election, reference, and disabled. |
| **Alert** | An editorial work item created when a check is overdue or detects a problem. | Dashboard delivery is the default future route; email is opt-in and ticketing is deferred. |
| **Immutable** | Not edited or deleted after creation. | Corrections create a new record that supersedes the old one, preserving the audit trail. |
| **Superseded** | Replaced by a newer, authoritative version while retained for history. | Used for claims, ballots, and other versioned evidence. |
| **Retracted** | Withdrawn because it should no longer be presented as valid. | The record and reason remain in the audit history. |
| **Retired source** | A source URL intentionally removed from active use. | It cannot be silently reactivated; a replacement receives a fresh review. |
| **Direct-link/manual-check** | Permission to show a direct official link and have a human inspect it. | The initial-launch scope. It does not permit scraping, automated requests, private artifact retention, or public copies. |
| **Private retention** | Keeping a source artifact in protected storage as provenance evidence. | Requires explicit source-review approval and does not imply public redistribution rights. |
| **Public copy** | A controlled copy of source content served by BallotApp. | Requires explicit redistribution/display rights; otherwise only metadata and the official link are shown. |
| **Redistribution rights** | Permission to provide someone else's content to other people. | Reviewed independently from whether a source is free to view. |
| **Attribution requirement** | Rules specifying how the source owner must be credited. | Stored in the registry and applied to citations and permitted copies. |

## Product and team terms

| Term | Plain-language meaning | BallotApp usage |
| --- | --- | --- |
| **Epic** | A large body of related work that produces a meaningful capability. | The backlog progresses from foundations through data, resolution, editorial tools, public guide, operations, and expansion. |
| **User story** | A short description of value from a particular user's perspective. | Explains who needs a capability and why. It is not the implementation specification. |
| **Task** | A concrete piece of implementation or research work. | Usually small enough to complete and verify independently. |
| **Decision checkpoint** | A product or policy choice that must be made before implementation can safely continue. | Used when code cannot determine business rules, editorial standards, or acceptable risk. |
| **Acceptance / exit criteria** | Observable conditions proving that work is complete. | Prevents an epic from being marked complete merely because code exists. |
| **Backlog** | The ordered list of planned product work and decisions. | The source of truth for completed, active, and future epics. |
| **Initial launch / pilot** | The deliberately narrow first production use of the product. | Copperas Cove 2026 with direct links and manual source checks. |
| **MVP (minimum viable product)** | The smallest product that delivers the intended value safely. | Must still meet privacy, sourcing, accessibility, and correctness requirements. “Minimum” does not mean unverified. |
| **Guardrail** | A rule that constrains design or implementation to avoid unacceptable harm. | Examples include no stored voter addresses and no unreviewed external services. |
| **Researcher** | A staff role that gathers and organizes evidence. | Can prepare drafts but does not automatically publish them. |
| **Verifier** | A separate role that checks evidence and accuracy. | Supports two-person review for ballot-critical information. |
| **Editor** | A role that resolves research questions and prepares content for publication. | Handles source changes, corrections, and unresolved evidence. |
| **Publisher** | A role authorized to make verified content public. | Publication actions are audited. |
| **Administrator / operator** | A person responsible for system configuration and reliable operation. | Runs migrations, deployments, backups, and temporary command-line editorial workflows. |
| **Nonpartisan product** | A product that does not support or oppose candidates, parties, or measures. | It may explain differences and publish attributed positions while applying the same rules to all sides. |

## Application and API terms

| Term | Plain-language meaning | BallotApp usage |
| --- | --- | --- |
| **Frontend / web app** | The pages and controls a person uses in a browser. | The Next.js application in `apps/web`. |
| **Backend / API service** | Server-side code that applies rules and exchanges data with the frontend or external consumers. | The FastAPI application in `apps/api`. |
| **API (application programming interface)** | A documented way for software systems to request or submit data. | BallotApp separates public civic, future editorial, and future partner API families. |
| **Endpoint** | One API operation at a specific method and URL path. | Example: a health check or ballot-resolution request. |
| **API version** | A compatibility boundary for a family of endpoints. | Public endpoints begin under `/api/v1`; breaking changes require a new major version. |
| **API contract** | The documented request, response, validation, error, and authorization behavior of an API. | Generated from code and tested so implementation and documentation stay aligned. |
| **OpenAPI** | A standard machine-readable description of an API. | Published at `/openapi.json` and usable for documentation or client generation. |
| **Swagger UI** | An interactive web page generated from OpenAPI for exploring and testing endpoints. | Available at `/docs`; it is documentation tooling, not a separate API. |
| **ReDoc** | Another human-readable presentation of the OpenAPI contract. | Available at `/redoc`. |
| **Request / response** | Data sent to an API and data returned by it. | Address input exists only for the lifetime of its request and is not echoed or persisted. |
| **CORS** | Browser security rules controlling which websites may call an API. | Configured to allow the approved web origin while preventing unintended browser access. |
| **Request ID** | A non-sensitive identifier used to trace one request across system logs. | Must not contain an address or other PII. |
| **Rate limit** | A rule limiting how many requests a caller may make in a period. | Planned for public/partner APIs and reviewed for every external provider. |

## Database and data-model terms

| Term | Plain-language meaning | BallotApp usage |
| --- | --- | --- |
| **Database** | An organized system for storing and querying structured data. | PostgreSQL is the authoritative application database. |
| **PostgreSQL / Postgres** | The open-source relational database engine used by BallotApp. | Stores tenant, provenance, authority, election, ballot, and editorial records. |
| **PostGIS** | A PostgreSQL extension for map shapes and geographic calculations. | Added in Epic 3 for official, versioned boundaries and future point-in-polygon district resolution. |
| **Schema** | The definitions of tables, fields, relationships, indexes, and constraints. | Encodes important safety rules in the database rather than relying only on application code. |
| **Table / row / column** | A table groups one kind of record; a row is one record; a column is one field. | For example, one authority is a row in the authority table. |
| **Primary key / UUID** | A stable unique identifier for one record. | UUIDs avoid requiring one central number sequence across tenants and deployments. |
| **Foreign key** | A database rule requiring a reference to point to an existing related record. | Prevents a document from silently pointing to the wrong authority or source. |
| **Constraint** | A database-enforced validity rule. | Rejects invalid states such as public copies without the required permission. |
| **Index** | A structure that helps the database find records efficiently. | Added for tenant, publication, election date, source status, and other common lookups. |
| **Migration** | A versioned change to the database schema. | Applied in order through Alembic before the API starts. Migrations are forward-only in this provenance model. |
| **Alembic** | The Python migration tool used with PostgreSQL/SQLAlchemy. | Tracks the current revision and applies pending schema changes. |
| **ORM / SQLAlchemy** | Code that helps Python communicate safely and consistently with a relational database. | SQLAlchemy provides connection and query infrastructure; explicit SQL is also used where appropriate. |
| **Tenant** | One organization/customer boundary in a shared hosted system. | An organization and its publications form the future tenant boundary. A self-hosted installation may have only one. |
| **Organization** | The top-level owner/operator of one or more publications. | Examples could eventually include a nonprofit, city partner, or media organization. It is not the same as an election authority. |
| **Publication** | One branded civic-information product or geographic edition operated by an organization. | The Copperas Cove guide is a publication. One publication can cover several authorities. |
| **Multi-tenant** | One hosted system safely serving multiple organizations with isolated data and access. | Planned without requiring every self-hosted deployment to use multiple tenants. |
| **Single-tenant** | One deployment/database serving one organization. | The natural self-hosted mode. |
| **Row-level security (RLS)** | PostgreSQL rules restricting which rows a database user/session may access. | Planned before hosted multi-tenant editorial access. |
| **Checksum / SHA-256** | A fingerprint calculated from file bytes. | Detects duplicate artifacts and later tampering without using the filename as identity. |

## Deployment, testing, and security terms

| Term | Plain-language meaning | BallotApp usage |
| --- | --- | --- |
| **Container** | An isolated process packaged with its runtime and dependencies. | Web, API, migrations, PostgreSQL, and Valkey run as separate containers locally. |
| **Container image** | The read-only package used to start a container. | Built reproducibly and scanned before deployment. |
| **Docker** | Tooling for building and running container images. | Used for local development and single-server deployment. |
| **Docker Compose / Compose stack** | A file and command that start several related containers together. | `compose.yaml` starts the current BallotApp stack. |
| **Kubernetes** | A platform for running and managing containers across servers. | A future/optional deployment target using standard manifests. |
| **Rancher** | A management layer commonly used to operate Kubernetes clusters. | BallotApp's Kubernetes manifests avoid Rancher-specific application dependencies. |
| **Bare metal / single server** | Running software directly on one host rather than on a managed cluster. | Supported using the same application images. “Bare metal” may still be a virtual server. |
| **DigitalOcean** | A hosting provider offering virtual servers, managed databases, and Kubernetes. | A possible host, not an architectural dependency. |
| **Valkey / cache** | An open-source in-memory data service used for temporary, rebuildable values or coordination. | Must never become a hidden store for entered voter addresses. |
| **Object storage** | Storage designed for files addressed by keys rather than database rows or local filenames. | Abstracted so private provenance artifacts can use a local volume or a future compatible service. |
| **Environment variable** | Configuration supplied to a process outside source code. | Used for database URLs, passwords, origins, ports, and storage paths. Secrets must not be committed. |
| **Secret** | Sensitive configuration such as a password, token, or private key. | Supplied through environment/secret management and excluded from logs and Git. |
| **CI (continuous integration)** | Automated checks run when code changes. | Builds, tests, audits, license checks, scans, and migration validation run before merge/release. |
| **Runner** | The machine or service that executes CI jobs. | May be an approved hosted runner or a self-hosted runner. |
| **Dependency** | A third-party library, runtime, image, API, or service the project relies on. | Must have reviewed licensing, cost, security, and usage terms. |
| **Lockfile / pinned version** | A record fixing exact dependency versions and package hashes. | Makes builds repeatable and makes upgrades deliberate. |
| **Package hash** | A cryptographic fingerprint for a downloaded dependency file. | Installation fails if downloaded bytes do not match the reviewed lockfile. |
| **Vulnerability** | A known security weakness in code or configuration. | CI blocks configured high/critical findings until fixed or explicitly reviewed. |
| **Security context** | Operating-system restrictions applied to a container or Kubernetes workload. | Used to prevent root privileges and reduce what a compromised process can do. |
| **SBOM (software bill of materials)** | A machine-readable inventory of software components in a build. | Generated for release review and vulnerability/license tracking. |
| **Health check** | A small test used to determine whether a service is functioning. | Liveness and readiness have different meanings. |
| **Liveness** | Whether the application process is running and responsive. | A failed liveness check may justify restarting the container. |
| **Readiness** | Whether the service can actually handle work, including required dependencies such as PostgreSQL. | Traffic should not be sent to an unready API. |
| **Backup / restore** | Creating a recoverable copy and proving it can rebuild the system's data. | A backup is not trusted until restoration has been tested. |
| **Incident** | An event that threatens privacy, accuracy, availability, or data integrity. | Severity and response steps are defined in the operations runbook. |

## Status words used in the project

| Status | Meaning |
| --- | --- |
| **Draft** | Work exists but is not approved for public use. |
| **Pending review** | A decision or evidence check is still required. |
| **Needs review** | Content has a known reason to require human attention. |
| **Verified** | Evidence has been checked under the required workflow. |
| **Published** | Approved content is currently visible to its intended audience. |
| **Unchanged** | A manual source check found no relevant difference. |
| **Changed** | A source check detected a difference requiring editorial review. |
| **Unavailable** | The source could not be accessed during the check. This does not prove permanent removal. |
| **Terms changed** | The source's license, privacy, access, or reuse terms appear different and must be reviewed again. |
| **Resolved** | An alert or investigation has been handled with a recorded outcome. |
| **Unresolved / needs review** | The system lacks sufficient evidence to return a trustworthy result. |
| **Ambiguous** | More than one plausible result exists and the system must not guess. |
| **Source conflict** | Authoritative sources disagree and a human decision with evidence is required. |
| **Archived** | Retained for history but no longer active. |

When a project document uses a term differently or introduces a new domain
term, update this glossary in the same change.
