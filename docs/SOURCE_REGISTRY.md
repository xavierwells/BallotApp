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
