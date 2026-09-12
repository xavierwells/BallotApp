# Editorial verification workflow

## Pilot policy

The owner approved loading source-backed material before review. New material
starts as a private, unreviewed draft. One human review suffices for official
candidate names, offices, party labels, and faithfully transcribed official
wording. Interviews, candidate statements, interpretive summaries, and other
editorial material require two distinct human reviewers of the final content.
AI never counts as a human reviewer. Review preserves the distinction between
a fact, a candidate statement, and analysis.

Conflicting evidence and uncertain ballot applicability remain unresolved until
the evidence supports a conclusion. Accepting names from a certification does
not establish a voter's ballot.

This supersedes the earlier instructions requiring independent sign-off before
loading drafts and two additional reviewers for every official fact.

## Start the workspace

From the repository root, after the already-successful source download:

First run the isolated database checks described below. If they fail, stop and
resolve the failure before migrating the pilot database. Back up the existing
pilot database using the deployment runbook before a schema upgrade.

```powershell
docker compose up -d --build
docker compose run --rm -it api python -m app.cli.prepare_pilot_review --username xavier
```

The first command applies migrations through `018_shared_race_reviews`. The second
prompts privately for a passphrase (15–256 characters), synchronizes the source
registry, records the previously approved narrow official-fact source-use
decision if still pending, registers the downloaded PDF, and loads three
private county batches. It does not retrieve the PDF again or verify any facts.

Open [the editorial workspace](http://localhost:3000/editorial) and sign in.
A repeated setup preserves the existing password, browser corrections and decisions
when the intake manifest is unchanged. Rejected/retired sources and conflicting existing source
permissions are not overridden.

This installation already has three county tasks and a staff account. For the
018 update, run the isolated tests, back up, and rebuild; do not repeat setup or
download the PDF. Existing batches and review history are retained.

If the API says storage is unavailable, check `docker compose logs migrate`
and confirm `018_shared_race_reviews` in `alembic_version`.

## Review without a shell

1. Choose Bell, Coryell, or Lampasas from the task queue.
2. Choose a source page. Read the retained PDF beside the extracted race and
   candidate table; open the PDF in a separate tab if the embedded viewer is
   unavailable. The screen shows both the printed citation and the physical PDF
   page. The SOS certification's cover makes PDF pages one higher (printed 271
   is PDF page 272); this is accounted for automatically. Confirm the printed page number.
3. Each office/race remains one section with its candidate table. Choose
   **Accept** after checking all its names, office title and party labels, or
   **Flag** if anything is wrong. A flagged section gets its own notes box.
4. For a transcription mistake, choose **Correct our transcription** inside
   that section. Type the corrected office title or candidate name, or choose
   the correct party. The value must match the cited PDF. If the official source
   itself appears wrong, leave a source-issue note instead of rewriting its label.
5. Select **Submit review** at the bottom to save all your pending section
   decisions and corrections together, including choices on other pages of this
   county. Nothing autosaves. Untouched sections are not accepted. Unsaved
   choices survive page navigation and failed submissions, but are not persisted
   across reload/sign-out; the browser warns before discarding them.
6. A correction creates a new private revision and stays flagged. Compare the
   updated text with the PDF, then Accept that section in a later submission.
   The same reviewer can do this; official facts do not need a second person.
7. Matching state/federal race content already reviewed in another county is
   labeled **Shared content reviewed**. No repeated acceptance is needed. Check
   the remaining unique/differing sections. If shared reviews are used, confirm
   once that this county's listed contests appear on its cited pages; you do not
   need to recheck shared names/parties. This does not establish voter applicability.
8. Once the county has no pending or flagged races and no unsaved changes, select **Import reviewed
   county**. This creates unpublished civic records. Other counties can remain
   unreviewed; this operation does not create a ballot style or publish a guide.

The master submit is one transaction: an invalid section or failed correction
cannot partially save other decisions. A field correction records before/after
values, signed-in reviewer, time and note. Expand **Correction history** to see it.
The retained PDF, original extraction and earlier decisions are not overwritten.

A reviewer can replace their own flag with a later acceptance after resolving
the issue. A flag from another reviewer still needs resolution. Unchanged
sections keep their reviews when the source document and all election/context
metadata are identical; they display **carried forward**. Changed sections lose
their acceptances, while unresolved flags remain visible for the same source.
Restoring an older spelling does not restore its old acceptance. A new source
document or changed election/context requires fresh acceptance throughout.

Browser corrections currently cover office title, candidate name and party.
Adding/removing candidates, changing jurisdictions or source citations still
requires a controlled manifest revision. Re-running setup with the original,
unchanged intake file does not undo browser corrections.

Once a revision is imported, its decisions are closed. Corrections create
another revision; a conflict with existing canonical records stops import.
Automated correction/supersession of already imported records remains future
work and is not implemented as a silent overwrite.

See [shared race review](SHARED_RACE_REVIEW.md) for matching rules, separate county
coverage and the immutable evidence receipt. Shared review never creates a fake
human check of another county page. An AI comparison is not a guarantee and must
not be submitted under a person's username as if they performed that review.

## What the application enforces

- Unreviewed batches are stored independently from canonical/public data.
- Staff accounts belong to one publication; other-publication batches and PDFs
  return 404. There is no public account registration.
- Review decisions use the signed-in staff identity and immutable draft revision.
- Intake, decisions and import serialize on the publication to prevent a new
  draft racing approval. Repeated imports are safe.
- Canonical certification import requires current, complete recorded review and
  active source retention approval. A Markdown sign-off alone does not satisfy it.
- Migration 016 replaces the blanket ballot reviewer count with one
  authenticated review of the current official ballot content. Its citation,
  official-source and geographic requirements remain in force.
- Source-claim publication requires one authenticated reviewer for an official
  `verified_fact`, or two for other claim/source types. A content fingerprint
  prevents approvals for old text from qualifying after an edit. Legacy
  free-text actor references cannot satisfy the new gates.
- Certification decisions do not count as ballot-version approval. There is no
  ballot/claim publication screen or review endpoint in this slice. The database
  policy is ready for that later publication handoff.

## Staff access and privacy

The pilot uses local provisioned accounts and the existing application/database.
No new authentication service or application package is required. Passwords are
stored as salted PBKDF2-HMAC-SHA256 hashes (600,000 iterations); session tokens
are random, stored hashed server-side, and expire after eight hours. Cookies
are HttpOnly and SameSite=Strict; production uses Secure cookies. Five failed
attempts lock an account for five minutes. A successful new login revokes that
account's earlier session. This first release supports one active session per
staff account.

All mutations require the configured `PUBLIC_WEB_ORIGIN`. Private API responses
use `Cache-Control: no-store`. Staff names, password hashes and audit identities
are separate from voter resolution; no voter account or address storage is added.

Use HTTPS and a same-site web/API deployment in production (for example
`ballot.example.org` and `api.example.org`), with an appropriate login rate limit
at the ingress. Local HTTP on localhost works in development. Keep the default
pilot installation private while the new integration tests and release checks
are completed. Password recovery and staff administration UI are not part of
this first slice; the operator CLI provides password reset and account disable.

For example, reset a forgotten passphrase with:

```powershell
docker compose run --rm -it api python -m app.cli.editorial_user reset-password --username xavier
```

The same tool supports `create` for an additional reviewer and `disable` to
revoke staff access. Reset and disable revoke sessions while preserving review
history; resetting a disabled account does not reactivate it.

Password implementation references:
[Python hashlib](https://docs.python.org/3/library/hashlib.html#hashlib.pbkdf2_hmac)
and [OWASP password storage guidance](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html).

## Verification and remaining work

Operator checkpoint: **85 passed, 10 warnings**, followed by successful setup
of three private county tasks under the 015–016 workflow. This confirms intake
and staff provisioning, not completion of content review.

Engineering checks for the 018 update on 2026-09-12: **142 passed, 13 skipped,
1 warning**. The thirteen database-backed tests require Docker/PostGIS unavailable in
this shell; the existing Starlette/httpx warning remains. Migration 018 renders
as offline SQL; execution against PostgreSQL is still pending. Five frontend
unit tests and the production web build pass. Mocked browser checks cover mixed
section decisions, correction history, separate acceptance, retry without losing
edits, page navigation, sign-out discard protection and desktop/mobile layouts.
Shared-review browser checks also verify donor attribution/source links, no
prefilled local acceptance, county confirmation, stale evidence handling and
the ability to flag a shared section.
These do not replace testing against the real API and private PDF.

The dependency audit found new advisories against Next.js 16.3.1, so the lockfile
now pins patched 16.3.3. The clean install reports zero npm vulnerabilities.
See the [Windows-server advisory](https://github.com/advisories/GHSA-p293-qw3h-jr36)
and [image-optimization advisory](https://github.com/advisories/GHSA-2xp9-vwfh-vxw4).
No new runtime libraries were added for editorial authentication or review.

```powershell
make api-test
docker compose --profile tests run --build --rm api-test
```

The second command exercises migrations, private document intake, sign-in,
review, flags, revisions, publication isolation, canonical import and the
one-/two-review publication policy against a separate PostGIS service. It never
uses the pilot database. Stop that temporary service after testing with
`docker compose --profile tests stop test-postgres`.

The web Docker build also runs the frontend unit tests with Node's built-in
test runner; locally, run `npm test` from `apps/web` with the supported Node version.

Pending: operator verification of migration 018 and the updated review UI;
staff administration screen; correction/supersession of already imported records;
official ballot and editorial publication screens; general interview intake.
Exact ballot styles and authoritative geography remain Epic 3 work.

See [the backlog](PRODUCT_DELIVERY_BACKLOG.md),
[certification staging](CANDIDATE_CERTIFICATION_STAGING.md), and
[human actions](HUMAN_ACTION_REGISTER.md).
