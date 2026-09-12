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

## Latest confirmed progress

The operator confirmed `85 passed, 10 warnings` and successful setup of three
private county tasks under the 015–016 workflow. The private PDF is downloaded,
checksum-matched and registered, and staff provisioning is complete. This does
not complete H-014 or establish a new CI run. Migrations 017–018's section
correction/shared-review workflows still need database and operator verification.

The [verification workflow](EDITORIAL_VERIFICATION_WORKFLOW.md) supplies two
test/upgrade commands and first-time setup instructions. Existing tasks need no
repeat setup or download. H-014 uses saved UI decisions; the Markdown
packet is an optional checklist, not an approval bypass.

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
| H-009 | Complete | Owner approved private unreviewed intake, one human for basic official facts, and two distinct humans total for interpretive content. Pilot staff accounts are locally provisioned and publication-scoped. | Decided 2026-09-11. | Owner approval; editorial workflow; migrations 015–016 and authenticated review code. | Policy no longer blocks basic-fact review. Recruit a second human before interpretive publication. |
| H-010 | Complete | Multi-source candidacy architecture approved: preserve certification and ballot citations; store party label on the election-specific candidacy; keep certification-only records draft and visibly incomplete. | Decided 2026-09-11. | Migration `014_candidate_sources`, staging documentation, and owner approval. | No longer blocks technical promotion; H-014 review still blocks reviewed promotion. |
| H-011 | Decision | Decide whether BallotApp may emit aggregated coarse-area signals for unresolved outcomes, covering `source_conflict`, `ambiguous`, `needs_review`, and `not_found`. | Before operational analytics or conflict-volume monitoring. | Granularity, minimum aggregation threshold, retention, access, deletion, and privacy approval. | Privacy-safe resolution monitoring. |
| H-012 | Waiting | Perform keyboard, zoom, mobile, screen-reader, and reduced-motion testing and record the release accessibility review. | Before public beta and every release. | Test date, tester reference, browser/assistive technology, findings, remediation owner. | Public launch. |
| H-013 | Decision | Select a search-as-you-type address provider or approve a self-hosted address dataset after privacy, license, cost, retention, and operational review. | Optional; native saved-address autofill is sufficient for the pilot. | Provider decision and complete source/service review. | Full address typeahead only. |
| H-014 | Ready | Continue the three loaded county tasks at `/editorial`. Xavier can review basic official facts once; matching state/federal content reuses that human review in other counties. Review unique/differing sections, then confirm each receiving county's contest list against its source before import. Typed corrections need later acceptance. | Before reviewed canonical promotion; download/setup complete. Validate migration 018 first. | Actual human decisions, source checksum/pages, correction history and immutable import receipt distinguishing shared content from county coverage. AI checks cannot be recorded as Xavier's human review. | Reviewed promotion of 108 county-scoped race entries and 216 candidate entries; exact duplicates do not require repeated content review. |

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

## Public contact route (email confirmed; website not deployed)

Owner confirmed Namecheap email delivery and SPF/DKIM/DMARC PASS for the main
mailbox. Local pages link `info@copperascovevotes.org` for contributions/questions
and `corrections@copperascovevotes.org` for mistakes; both reach Xavier's mailbox.
`/contribute` explains evidence, email retention and review, not an upload form.
The owner selected `copperascovevotes.org` through Namecheap, with a preferred
hosting budget under USD 10/month. See [the setup plan](DOMAIN_AND_EMAIL_SETUP.md).
The website is not ready for deployment. After explicit owner approval and
deployment, test these links and public pages over HTTPS before inviting submissions.

Before announcing uploads, confirm the public intake route actually accepts
material privately and returns a receipt. Before announcing published coverage,
confirm real reviewed ballot records are available. The private staff dashboard
alone does not satisfy either launch claim.

## Completed human actions

| ID | Completed | Action | Evidence |
| --- | --- | --- | --- |
| H-C01 | 2026-08-20 | Reviewed and promoted the pinned 76522 Census coverage calculation. | API returns reviewed Coryell 94.7766% and Lampasas 5.2234% area matches with `demonstration: false`. |
| H-C02 | 2026-08-20 | Verified the Compose stack, PostGIS migration chain, API readiness, and current containerized test suite. | User-reported stack health and `53 passed, 1 skipped, 1 warning`. |
| H-C03 | 2026-09-11 | Retrieved and checksum-pinned the Texas SOS 2026 ballot certification and staged its complete Coryell County section without publishing or creating ballot styles. | SHA-256 `c13ffb4ebeee389fa9818d47b31f77b4e260ea6e6f5389cb7bf0f36d9b44d87c`; 5,919,631 bytes; 36 races and 70 candidates on report pages 271–275. |
| H-C04 | 2026-09-11 | Approved the multi-source candidacy direction and election-specific party labels. | Implemented by forward migration `014_candidate_sources`; citations are immutable and tenant-scoped. |
| H-C05 | 2026-09-11 | Staged the Bell and Lampasas sections and recorded newly visible Copperas Cove/CCISD source evidence without application PII. | Bell: 40 races/79 candidates, pages 70–75. Lampasas: 32 races/67 candidates, pages 783–787. Local discovery remains non-promotable pending official mapping. |
| H-C06 | 2026-09-11 | Operator confirmed migration 014, the successful private source download, and the container tests. | `014_candidate_sources`; 5,919,631 bytes; SHA-256 `c13ffb4ebeee389fa9818d47b31f77b4e260ea6e6f5389cb7bf0f36d9b44d87c`; `67 passed, 1 skipped, 1 warning in 1.63s`. No editorial review is implied. |
| H-C07 | 2026-09-11 | Operator confirmed the 015–016 database tests and successful private editorial setup. | `85 passed, 10 warnings`; three private county tasks ready. No facts automatically verified or published; H-014 remains open. |
