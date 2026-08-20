# Source registry and authority intake

This document defines Epic 2's authority and source registry. It is the
control point for external election information: registering a URL is not an
approval to retrieve, redistribute, or automate against it.

## Model boundaries

- An **election authority** is an organization that administers or is the
  authoritative publisher for an election record. It is not a geographic
  district.
- A **source registry entry** is a reviewed external endpoint owned by an
  authority, such as an election-information page, notices page, ballot
  repository, or results page.
- A **document** is an immutable retrieved or manually uploaded artifact. It
  can cite a registry entry, but must retain its own URL, retrieval timestamp,
  SHA-256 checksum, and any permitted storage key.
- A geographic district is created only from boundary evidence in Epic 3. A
  document intake can create a *draft authority*, but cannot infer or create a
  district merely because its text includes a district name.

This keeps the registry extensible: later cities, counties, and special
districts are rows, rather than schema changes. A source added with a new
ballot remains pending review until its authority and reuse terms are known.

## Required review workflow

1. A researcher records the authority and source URL as `pending_review`.
2. The reviewer records the owner, purpose, direct URL, terms/license URL,
   cost, rate limit, retention rule, attribution requirement, and
   redistribution rights.
3. The project owner (or a delegated role defined in Epic 4) approves,
   rejects, or retires the source. Approval records the reviewer and time.
4. Only an approved entry can be selected for automated retrieval. Manual
   intake still records the entry's review status so an editor can see when a
   document came from an unapproved source.
5. A changed URL, terms, or provider policy requires a fresh review; the old
   entry is retired rather than silently changed.

An official government domain is evidence of ownership, not a blanket
license to redistribute documents or use an API. Pending entries are safe to
catalog but not yet eligible for automated retrieval.

For the initial launch, the Copperas Cove pilot sources use the deliberately
narrow `direct_link_manual_check` scope. It allows a direct attribution link
and a human's manual check of that link; it does **not** authorize private
artifact retention, public copies, scraping, or scheduled automated requests.
This scope is recorded separately from `approval_status`, so the registry does
not misrepresent a product policy as a source-content license.

Until Epic 4 provides authenticated editorial roles, the review decision is an
operator-only local command. Approval requires every review field that the
database constraint requires; the command never contacts the external URL.

```sh
cd apps/api
python -m app.cli.review_source \
  --organization-slug whats-on-my-ballot \
  --publication-slug copperas-cove \
  --authority-slug city-of-copperas-cove \
  --source-slug election-information \
  --approval-status approved \
  --permitted-use private_retention \
  --reviewer-reference editor-123 \
  --terms-url https://authority.example/terms \
  --source-license "public-record terms reviewed" \
  --cost-model free \
  --rate-limit "no automated use approved" \
  --retention-rule "retain privately for provenance" \
  --attribution-requirement "cite the authority and source URL" \
  --redistribution-rights metadata_only
```

`--automated-monitoring-allowed` is opt-in and accepted only with an
`approved` decision and a non-zero permitted-use scope. A retired source
cannot be reactivated; register a replacement source for fresh review instead.

## Retention and visibility policy

Every accepted source artifact is retained privately as provenance evidence,
using a checksum-addressed storage key. This is distinct from public display:

- `metadata_only` is the default whenever public-display or redistribution
  terms are absent, unclear, or not yet approved. Public responses may show
  the title, authoritative source URL, retrieval time, checksum, and citation,
  but not the retained file or its extracted content.
- `public_copy` is allowed only after the source review records explicit
  rights for that use. The public API/UI still serves a controlled copy rather
  than exposing object-storage paths.

The retained artifact is private to the deployment and is never exposed by a
  storage URL. The forthcoming manual intake flow records its byte length and
  storage key in `documents`; it does not fetch a source merely because it was
  registered.

## Verification cadence and stale-source queue

The built-in cadence is the approved starting policy, applied by monitoring
class rather than indiscriminately to every source:

- `active_ballot`: daily only after an official ballot is available and the
  authority has an election within 90 days; weekly during that window before
  the ballot is available.
- `active_election`: weekly during the final 90 days.
- `reference`: monthly, including during an active election.
- `disabled`: never queued unless an editor deliberately changes the class.

An approved source may be monitored automatically only when its reviewed terms
explicitly permit that method (`automated_monitoring_allowed`). Otherwise a
dashboard task is created only at the relevant cadence. Automated checks look
for availability or change signals; they do not publish a change. A human
reviews every exception, retains any replacement artifact, and updates ballot
data through the normal verification workflow.

`verification_cadence_policies` accepts one policy at each scope, resolved in
this order: election authority, publication, organization, then the built-in
policy. This supports a single self-hosted tenant with no configuration as
well as hosted publication and authority overrides. `source_verification_checks`
keeps immutable check history, while `authority_source_registry.next_check_at`
drives the future queue/alert job. No external retrieval is enabled by this
schema; a check must be explicitly performed and recorded.

Until Epic 4 provides the authenticated dashboard, an operator records a
completed **manual** check through the local command below. It is deliberately
tenant-scoped and requires the source to be approved. The operator supplies
the next due time after applying the active cadence policy; the command does
not retrieve the URL or attempt to decide whether a ballot is official.

```sh
cd apps/api
python -m app.cli.record_source_check \
  --organization-slug whats-on-my-ballot \
  --publication-slug copperas-cove \
  --authority-slug city-of-copperas-cove \
  --source-slug election-information \
  --result unchanged \
  --checker-reference editor-123 \
  --next-check-at 2026-08-27T12:00:00Z
```

The completed check is immutable. Database triggers update the source's
`last_checked_at` and `next_check_at` only when the new check is not older
than the recorded one. A `changed`, `unavailable`, or `terms_changed` result
opens its corresponding investigation alert automatically.

## Stale-source alert delivery

The editorial dashboard is the required default destination for an overdue
source. It is the only delivery channel enabled in a fresh deployment.

- An authenticated editor may later opt in to email notifications for the
  dashboard alerts they are permitted to see. Email is never enabled solely
  because an account exists.
- A ticketing-system integration is a future optional adapter. It remains
  disabled until a provider, authentication method, routing rules, and data
  disclosure review are approved; no provider is assumed by this project.
- Alert data is editorial operational data only. It must not contain entered
  addresses, voter information, or private object-storage URLs.

The dashboard, editorial identities, notification preferences, and ticketing
adapter configuration are implemented in Epic 4, where their authorization
boundaries can be enforced.

## Hybrid alert lifecycle

An overdue-source alert is automatically resolved only when a **manual** check
records `unchanged`. The resolution is retained as `automatic_unchanged` and
links to that immutable check record. An automated no-change signal cannot
close an alert by itself.

Checks that find a changed, unavailable, or terms-changed source keep the
associated investigation alert open. An authorized editor will later resolve
it explicitly after retaining a replacement artifact, updating the registry,
or retiring the source. `source_alerts` stores this state now; its dashboard
workflow is intentionally deferred to Epic 4.

Before the dashboard's scheduled worker exists, an operator can queue overdue
work with a local, repeat-safe command. It only evaluates database timestamps;
it makes no network request and creates no duplicate open alert.

```sh
cd apps/api
python -m app.cli.queue_overdue_source_alerts
```

## Copperas Cove pilot registry

The initial, editable manifest lives at
[`data/authorities/copperas-cove-pilot.json`](../data/authorities/copperas-cove-pilot.json).
It contains the authorities currently in the pilot's jurisdictional scope:

- City of Copperas Cove
- Coryell County
- Bell County
- Lampasas County
- Copperas Cove Independent School District
- Texas Secretary of State, Elections Division

All associated URLs start as `pending_review`. No special district is
pre-registered until an official election order, ballot, or boundary source
establishes that it is applicable; a newly identified one is added as a draft
authority through the same process.

After `002_authority_source_registry` has been applied, an operator can load
the local manifest without fetching any remote content:

```sh
cd apps/api
python -m app.cli.bootstrap_authorities
```

The command is safe to repeat. It creates the publication if needed, upserts
authority metadata, adds only new pending-review sources, and refuses to
silently change an existing source URL.

Compose mounts this editable manifest into the API container read-only at
`/app/data/authorities`; the API image itself does not embed pilot-specific
configuration. A self-hosted operator can supply another local manifest with
the command's `--manifest` argument or the `AUTHORITY_MANIFEST_PATH`
environment variable.

## Manual document intake

Until authenticated editorial roles arrive in Epic 4, document intake is an
operator-only command rather than a public HTTP endpoint. It takes a local
artifact and its source metadata; it never fetches the `--source-url`.

```sh
cd apps/api
python -m app.cli.intake_document \
  --authority-slug city-of-copperas-cove \
  --source-slug election-information \
  --file /protected/intake/notice.pdf \
  --title "Notice of Election" \
  --publisher-name "City of Copperas Cove" \
  --source-url "https://example.gov/notices/notice.pdf" \
  --document-published-at "2026-08-20T00:00:00Z"
```

The command validates the registry relationship, retains the supplied bytes,
records the checksum and size, and creates an immutable `documents` row. It
defaults to `metadata_only`; `--public-access-level public_copy` is rejected
unless the linked source registry entry has been approved. Repeating an intake
with an already retained checksum returns the existing document record.

## Citation presentation

`apps/web/app/components/SourceCitation.tsx` is the shared citation primitive
for ballot and editorial pages. It renders the publisher, official URL,
retrieval date, and optional page reference. For `metadata_only` documents it
links only to the official source; it never creates a link to the retained
artifact. Public API representations must provide the same fields before a
page renders this component.

## Intake rule for a new ballot

An editor may associate an intake with an existing authority or create a new
draft authority in the same editorial transaction. The intake must capture a
source URL and retrieval metadata. It must not create an authoritative
geographic district, attach a ballot to voters, or cause public publication.
Those need the source review, verification, and (later) boundary-resolution
controls respectively.
