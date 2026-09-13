# Shared race review

## One content check, several county entries

The owner approved reusing a human's review when the same certified race is
repeated across counties. County tasks remain a useful way to navigate the
source, but they are not separate requirements to reread identical names and
party labels. A reused review is identified as shared, with the original human,
time, county, draft revision and source page visible.

No review is written under the receiving county or another person's username.
An empty local decision list stays empty. This is reuse of an existing human
decision, not an additional reviewer or a claim that another PDF page was read.

The checked-in pilot staging files currently contain 108 county race entries
but 67 distinct content-review sections under these rules: 41 repeated checks
can be avoided. This is an inventory comparison, not confirmation that the
extraction or official source is correct. Browser corrections may change the totals.

## What matches

For the pilot, automatic sharing requires the same publication, registered
document/checksum and source metadata, election name/date/type, stable office
key, government level, jurisdiction and district. The office title, seats,
complete candidate roster and party labels must match exactly. Candidate order
and county page number are not shared evidence; neither is county applicability.
County administrator and intake retrieval time may differ.

State and federal races can match across counties. Local/county offices stay
county-scoped until we have reliable cross-county authority identifiers for
them. Two similarly named County Judge offices must not be merged.

- Only direct human decisions on current county revisions can supply evidence.
  Same-county carry-forward still works, with the original decision retained.
- A person's reviews in several counties count as one person, not several.
- Disabled reviewers cannot supply a qualifying acceptance.
- Differing text or an unresolved flag in a matching group pauses shared reuse.
  Local decisions remain separate; another county cannot erase a local flag.
- Corrections change only the selected county draft. Peers are never silently
  rewritten. Differences must be investigated, not assumed to be the same fact.
- Shared evidence is computed from current records; it cannot supply a new
  shared decision that loops back and makes itself appear independently verified.

## In the dashboard

1. Check and Accept a race in one county; submit normally.
2. Open another county. Fully reviewed pages, including those covered by shared
   reviews, are skipped automatically and shown in gray. Opening one asks for
   confirmation; it does not reset decisions. Exact matches show **Shared content reviewed**, with a
   link to the source page actually reviewed. Do not Accept them again merely
   to make the progress counter change. You may still flag a discrepancy.
3. Review the remaining county-specific or differing sections.
4. Before importing a county that uses shared reviews, make one county-level
   confirmation that its listed contests appear on its cited source pages.
   This is a contest-list/source-coverage check, not another name-by-name check.
5. Import the county as private records. This does not identify a voter's ballot,
   establish precinct boundaries, or publish anything.

When all content is reviewed, the county opens on an overview. The source PDF,
county-source confirmation and import remain available there; completed-page
navigation does not bypass the county confirmation requirement.

The import rechecks the evidence under the publication lock. If evidence changed
while the page was open, reopen the task and confirm against the refreshed view.
The import stores an immutable snapshot of the exact local/shared review basis
and the authenticated person who confirmed county coverage. Later changes do
not rewrite that historical receipt. It is evidence *as of import*, not approval
of future changes. Canonical correction and public publication remain separate.

The original county page citations stay attached to private draft facts. The
snapshot distinguishes those local source references from the donor pages where
candidate content was reviewed. Shared review does not certify local ordering.

## AI checks and staff identities

Plain text can still contain extraction, association, omission or source errors.
An automated comparison cannot guarantee accuracy. AI may prepare drafts or
report discrepancies, but must not record its work as a human's review (including
under `xavier`). Approval comes from the person submitting the authenticated
review. Automated work, if recorded later, must be explicitly attributed to the
automation and must not satisfy the human-review threshold.

## Deployment and tests

Migration `018_shared_race_reviews` adds a nullable review snapshot to existing
immutable promotion records. It does not rewrite past approvals or change the
original certification files. Rebuild after testing; no repeat setup/download
is needed. Existing qualifying human reviews become reusable automatically.

```powershell
docker compose --profile tests run --build --rm api-test
```

After the isolated tests pass, back up the pilot database and run:

```powershell
docker compose up -d --build
```

The test suite covers exact identity/content matching, county page separation,
distinct active humans, flags, corrections, stale import evidence, confirmation
gates and immutable import receipts. Database execution remains an operator
check when Docker/PostGIS is unavailable to the coding shell.

See [staff API](EDITORIAL_API.md) and [the review workflow](EDITORIAL_VERIFICATION_WORKFLOW.md).
