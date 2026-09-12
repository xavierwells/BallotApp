# 2026 candidate certification staging

The Texas SOS final August 28 certification was transcribed into three
page-cited staging manifests. The operator confirmed the private PDF download:
5,919,631 bytes, SHA-256
`c13ffb4ebeee389fa9818d47b31f77b4e260ea6e6f5389cb7bf0f36d9b44d87c`.
The file is in `data/private/2026-ballot-cert.pdf`, which is ignored by Git.

| County | Report pages | Race entries | Candidate entries |
| --- | --- | ---: | ---: |
| Bell | 70–75 | 40 | 79 |
| Coryell | 271–275 | 36 | 70 |
| Lampasas | 783–787 | 32 | 67 |

The 108 race entries and 216 candidate entries include contests repeated across
counties. Validation of these counts does not verify transcription accuracy.
Certification does not establish precinct-to-ballot applicability or include
every Copperas Cove/CCISD contest.

## Current workflow

The owner approved **load first as unreviewed, then one human review of basic
official facts**. The old instruction to obtain independent sign-off before
loading a draft is superseded.

```powershell
docker compose up -d --build
docker compose run --rm -it api python -m app.cli.prepare_pilot_review --username xavier
```

Setup asks for a passphrase when creating the account. It registers the retained
PDF and prepares the three private review batches. Open
[the review workspace](http://localhost:3000/editorial), compare facts with the
source, and choose Accept or Flag per office/race section. A flag has its own
notes and optional transcription corrections. Use **Submit review** at the
bottom to save all choices; no fact is automatically verified or autosaved.

The complete instructions and implemented limitations are in
[Editorial Verification Workflow](EDITORIAL_VERIFICATION_WORKFLOW.md).
No repeated download is required on this machine.
The existing three tasks are already loaded. For the 018 update, run the
isolated tests and backup/rebuild steps in that workflow; setup need not be repeated.

## Import is separate from review and publication

- Setup stores immutable, **unreviewed** batches for staff to inspect.
- Acceptance records a human review of the selected races and their labels.
- Identical state/federal race content can reuse an existing human review from
  another county. Its actual reviewer/page remain visible. Before a shared
  import, confirm once that this county's listed contests occur on its source
  pages; this does not establish precinct/voter applicability.
- **Import reviewed county** creates unpublished elections, races, candidates,
  party labels, and source citations once that county has complete review.
- The operation creates no ballot style, public guide, or exact-match claim.

The developer command `stage_candidate_certification --manifest ...` remains a
write-free validator. Its `--apply` mode writes canonical records and now checks
the current review batch in the database. A manual Markdown signature no longer
satisfies this check. Editors should use the import button after browser
corrections: it imports the reviewed revision, while an older local JSON file
will no longer match the latest corrected batch.

Edits to a manifest create a new county revision when setup is rerun. Unchanged
reruns preserve review progress and browser corrections. Changes require fresh
acceptance of changed sections; fully unchanged sections retain their reviews
when source and election/context also match. Browser label corrections retain
before/after values and stay flagged until accepted in a later submission.
Source snapshots and old decisions remain preserved. Canonical conflicts stop import
and need a correction/supersession workflow.

## First-time source download, when needed

For another installation without the private PDF:

```powershell
docker compose build source-fetch
docker compose run --rm source-fetch `
  --url "https://www.sos.state.tx.us/elections/forms/2026-ballot-cert.pdf" `
  --destination /app/data/private/2026-ballot-cert.pdf `
  --expected-sha256 c13ffb4ebeee389fa9818d47b31f77b4e260ea6e6f5389cb7bf0f36d9b44d87c
```

The one-shot service has a writable intake mount; the running API reads that
mount and maintains its separate private document store.

## Recorded checkpoint

The operator confirmed **85 passed, 10 warnings** and successful provisioning
of three private county review tasks under migrations 015–016. Migration
017 adds section-level corrections and preserved reviews; 018 adds shared
content reviews and an immutable import evidence receipt. Database execution
through `018_shared_race_reviews` and the updated UI still need operator verification.
No completed content review or canonical promotion is implied by setup/tests.

## Source use

This narrowly scoped official-fact intake uses the approved project policy:
public factual material, private provenance retention, source attribution,
metadata/facts rather than a public PDF mirror, and no automated crawler or
personal application records. Missing explicit terms are recorded as
uncertainty, not represented as a publisher-granted license. Setup preserves
an existing approval and stops on a rejected/retired or incompatible source.
