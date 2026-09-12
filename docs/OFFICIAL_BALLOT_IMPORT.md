# Official ballot manifest and draft import

The official-ballot importer turns one manually reviewed, already-registered
authoritative document into structured **draft** election data. It never
downloads a source and it has no publication option.

## Safety model

- The source document must already exist in `documents` for the same
  publication, be authoritative, use `official_document`, and match both the
  manifest checksum and HTTPS URL.
- Every race, candidate name, proposition, ballot item, ordering position, and
  geographic requirement comes from the pinned manifest; the importer does not
  infer missing facts.
- Every item requires a page or section citation into the official document.
- Geographic requirements require a human verifier reference and an existing
  active geographic area.
- Imports are transactional, idempotent, and drift-sensitive. Rerunning the
  same manifest is safe; conflicting or extra stored content causes failure.
- `--apply` creates only `draft` ballot versions. It cannot verify or publish.

The synthetic contract fixture is
`data/ballots/synthetic-official-ballot.json`. It contains no real candidate,
boundary, proposition, or ballot data.

## Dry run

```powershell
docker compose run --rm api python -m app.cli.import_official_ballot `
  --manifest /app/data/ballots/synthetic-official-ballot.json
```

Expected final line: `Dry run only; no database writes were made`.

## Real operator workflow

1. Complete the relevant source and permission actions in
   `HUMAN_ACTION_REGISTER.md`.
2. Register the exact official document with `intake_document`; this remains
   unavailable while the source is limited to `direct_link_manual_check`.
3. Create a manifest from the official ballot. Transcribe official wording
   exactly; do not add biographies or infer district membership.
4. Have a human compare it with the official document and supply each
   geographic `verifiedByReference`.
5. Run the dry run and review its counts.
6. Apply the same pinned manifest with `--apply`.
7. Review the drafts. One authenticated staff identity must record a `verified`
   event targeting the current official ballot content before publication can work.

This remains an interim operator workflow for **ballot styles**. The new staff
login and [review workspace](EDITORIAL_VERIFICATION_WORKFLOW.md) support the
county certification review, not ballot-style approval or publication yet.
Certification decisions cannot substitute for reviewing an assembled ballot.

## Database publication gates

Migrations `013_official_ballot_intake` and `016_review_policy` reject publication unless the ballot
has at least one verified geographic requirement, at least one ballot item, a
nonblank official-document page citation on every item, an authoritative official
document, and at least one authenticated staff review bound to its current
content fingerprint. Migration 016 supersedes the earlier two-reference rule.

Free-text actor references alone no longer qualify. Official factual claims need
one authenticated review; candidate statements and interpretive claims need two
distinct humans. Those general publication controls still need their own UI and
release acceptance; the certification workspace imports private facts only.

Once published, ordered ballot-item membership is immutable. Corrections use a
new ballot version and retain the historical version.

Migration `014_candidate_sources` allows the same candidacy and election to
retain additional official citations, such as a prior state certification,
without replacing either source. Party affiliation is election-specific. An
omitted `partyLabel` in a ballot manifest preserves an already certified label.
