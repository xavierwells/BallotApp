# Human action register

This is the centralized list of work that requires a person outside the normal
build/test workflow: outreach, permission, source judgment, editorial review,
manual audits, and operational sign-off. Engineering backlog items should link
here instead of hiding an external dependency inside a code task.

Do not place voter addresses, personal location, passwords, API keys, or
unnecessary personal contact data in this file, tickets, or outreach records.
Store a reply or permission document only when its retention is authorized;
otherwise record its date, sender's organizational role, disposition, and a
non-sensitive reference to where the operator keeps it.

## Status meanings

| Status | Meaning |
| --- | --- |
| Ready | A person can perform this now. |
| Waiting | Timing or an external publication blocks it. |
| Decision | The project owner or designated reviewer must choose and record a policy. |
| Recurring | Repeat on the stated cadence. |
| Complete | Evidence and completion date are recorded. |

## Active launch actions

| ID | Status | Human action | Timing | Evidence to record | Blocks |
| --- | --- | --- | --- | --- | --- |
| H-001 | Ready | Ask Coryell County Elections for the current November 3, 2026 voting-precinct GIS layer or legal descriptions; confirm that it supersedes or validates the TLC primary reference; request written terms for private retention, derived geometry, public attribution, and any automated checks. | Now | Date, office/role contacted, reply disposition, source URL or non-sensitive permission reference. | Exact precinct resolution and Coryell ballot-style mapping. |
| H-002 | Ready | Make the equivalent current-boundary and reuse request to Bell County Elections. Verify the county's linked ArcGIS layer, completeness, effective date, export method, and November applicability. | Now | Same fields as H-001. | Exact Bell County resolution. |
| H-003 | Ready | Make the equivalent current-boundary and reuse request to Lampasas County Elections. | Now | Same fields as H-001. | Exact Lampasas County resolution. |
| H-004 | Ready | Ask the City of Copperas Cove/City Secretary for current municipal boundary data, the authoritative 2026 election notice and eventual sample ballot, and written permission covering private evidence retention and permitted republication. | Now; follow up when ballot is published. | Date, office/role, URLs, effective dates, rights disposition, permission reference. | Municipal resolution and city ballot ingestion. |
| H-005 | Ready | Ask Copperas Cove ISD for the authoritative 2026 election notice, trustee-place/district applicability, eventual sample ballot, and written retention/republication permission. | Now; follow up when ballot is published. | Date, office/role, URLs, applicability explanation, rights disposition. | School-district ballot ingestion and exact mapping. |
| H-006 | Waiting | Obtain and manually inspect every official November 3, 2026 sample-ballot style affecting the pilot. Do not copy or retain files beyond the approved source disposition. | As soon as authorities publish them. | Authority, ballot/style identifier, publication/check date, URL, checksum only when retention is approved, and coverage notes. | Real ballot versions, races, candidates, and propositions. |
| H-007 | Ready | Contact the League of Women Voters of Texas or participating local League about a VOTE411 data export/media partnership, historical retention, attribution, correction handling, and permission to expose derived fields through BallotApp APIs. | Now; follow up when its guide is published. | Contact date and organizational role, requested fields, permitted uses, retention/redistribution terms, attribution, correction process. | Automated VOTE411 intake; manual links remain allowed after review. |
| H-008 | Waiting | Audit VOTE411, Ballotpedia, BallotReady, and other relevant guides against the official Copperas Cove ballot using the privacy-safe method in `PRODUCT_POSITIONING_AND_VALIDATION.md`. | Once official ballots are available and again 14–21 days before Election Day. | Aggregate contest-level coverage only; never the tested address. | Evidence-based product positioning and expansion decision. |
| H-009 | Decision | Designate at least two distinct editorial reviewers and approve how researcher, verifier, editor, and publisher identities will be authenticated and separated. | Before any real ballot item can be published. | Named internal identity references, approved workflow, decision date; avoid unnecessary personal data. | Two-person publication gate and real public content. |
| H-010 | Decision | Resolve whether provisional candidate records may exist before an official candidate document is attached, including minimum evidence and the visible incomplete-state label. | Before candidate-entry/import forms. | Written product decision and approver/date. | Candidate schema/workflow implementation. |
| H-011 | Decision | Decide whether BallotApp may emit aggregated coarse-area signals for unresolved outcomes, covering `source_conflict`, `ambiguous`, `needs_review`, and `not_found`. | Before operational analytics or conflict-volume monitoring. | Granularity, minimum aggregation threshold, retention, access, deletion, and privacy approval. | Privacy-safe resolution monitoring. |
| H-012 | Waiting | Perform keyboard, zoom, mobile, screen-reader, and reduced-motion testing and record the release accessibility review. | Before public beta and every release. | Test date, tester reference, browser/assistive technology, findings, remediation owner. | Public launch. |
| H-013 | Decision | Select a search-as-you-type address provider or approve a self-hosted address dataset after privacy, license, cost, retention, and operational review. | Optional; native saved-address autofill is sufficient for the pilot. | Provider decision and complete source/service review. | Full address typeahead only. |

## Source-response procedure

When an authority or partner replies:

1. Do not interpret a friendly reply as broader permission than its words grant.
2. Separate permission to link, privately retain, transform, redistribute, and
   automate access.
3. Record attribution, rate/cadence limits, effective dates, and revocation or
   correction requirements.
4. Update the source registry through the reviewed operator workflow.
5. Keep uncertain rights at `direct_link_manual_check` and escalate the
   decision rather than assuming public availability equals free reuse.

## Suggested VOTE411 request

Ask whether a nonprofit/local civic project may receive a structured export of
published races, candidates, candidate-submitted answers, ballot questions,
district identifiers, source fields, and correction updates for the Copperas
Cove pilot. Explicitly ask whether BallotApp may privately retain historical
versions, quote or republish fields, provide derived fields through a public
API, and preserve the data after Election Day. Request required attribution,
fees, rate limits, deletion duties, and a written correction/contact process.

## Completed human actions

| ID | Completed | Action | Evidence |
| --- | --- | --- | --- |
| H-C01 | 2026-08-20 | Reviewed and promoted the pinned 76522 Census coverage calculation. | API returns reviewed Coryell 94.7766% and Lampasas 5.2234% area matches with `demonstration: false`. |
| H-C02 | 2026-08-20 | Verified the Compose stack, PostGIS migration chain, API readiness, and current containerized test suite. | User-reported stack health and `53 passed, 1 skipped, 1 warning`. |
