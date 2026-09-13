# 2026 post-election transition

## Decision

The dynamic Copperas Cove pilot has a planned end rather than running by inertia.
The target cutover is **Monday, November 16, 2026**. The public domain then serves
a small static election archive while the dynamic web/API/database host is taken
out of public service after verification and backup.

Static hosting is budgeted at USD 0 after cutover. Domain registration remains
annual. The default is to retain the paid project mailbox through its first annual
term; a later switch to free inbound forwarding is a separate mail/DNS operation,
not part of the static-site cutover.

This date controls hosting operations, not the legal status of election results.
If an authority has not certified its results by November 16, the static page may
show the authority's latest published totals only when prominently labeled
**unofficial**, linked to the official source, and stamped with the retrieval time.
It must not predict winners or silently change an unofficial result to certified.
A later certification produces a new static build and preserves the earlier
source/version in the private provenance archive.

## Public static archive

The static site should contain only what remains useful after voting:

- election name and date;
- each covered contest and authority;
- the latest official published result totals, with `unofficial`, `canvassed`,
  or `certified` status exactly as supported by the authority;
- reporting completeness when the official source provides it;
- source link, source authority, retrieval/verification time, and a plain note
  explaining that the election authority is definitive;
- corrections and general-contact email links;
- a concise pilot-usage summary after the metrics privacy check; and
- an archival notice explaining that address lookup and the editorial workspace
  are no longer active.

The static export must contain no voter address, coordinate, staff session,
private review note, unpublished draft, private source document, database dump,
secret, or administrative route. It is an independently reviewable build artifact,
not a copy of the application data directory.

## Metrics that may be retained and published

For the pilot, “hits” means aggregate requests or completed actions, not unique
people. Do not claim a visitor count without a privacy-approved measurement that
actually measures people. Bots, reloads, retries, health checks and staff testing
must be excluded where practical and limitations must be stated.

Allowed aggregate candidates are:

- public page views by day;
- ballot lookup attempts by day;
- aggregate lookup outcome counts: resolved, ambiguous/source-conflict, and
  unavailable/not-found;
- area-browse requests by coarse area type (ZIP, city, or county), without the
  entered value;
- peak requests per minute and service uptime; and
- correction/contribution email counts recorded manually, without sender details.

Never retain or publish raw address text, coordinates, IP addresses, user-agent
strings, referrer URLs, cookies, session identifiers, email addresses, or small
geographic query values for analytics. Do not enable third-party tracking merely
to create the post-election summary. Prefer first-party aggregate counters. Raw
operational logs, if temporarily required for security, need a separate short
retention rule and are not an analytics dataset.

Before collection begins, the owner must approve definitions, bot/test filtering,
retention and minimum publication thresholds under H-011. Until then, the static
site may omit usage metrics; lack of metrics must never delay the safety cutover.

## Predetermined operating sequence

| Date/window | Action and gate |
| --- | --- |
| November 3 | Keep election mode active through the end of Election Day. Preserve corrections and source checks. Do not publish projected winners. |
| November 4 | Freeze non-correction voter-guide editing. Begin results intake from registered official authority sources; retain explicit result status. |
| November 4–13 | Reconcile contest identifiers and totals, record source versions, and perform the required factual review. Prepare the static export and a static-host rollback copy. |
| November 14 | Snapshot approved aggregate metrics; exclude post-election maintenance traffic. Create final dynamic-host database/document backups and perform a restore test. |
| November 15 | Generate and review the static artifact. Check every result/status/source link, mobile and keyboard behavior, correction/contact links, headers, HTTPS plan and absence of private material. Lower DNS TTL in advance if DNS switching is used. |
| **November 16** | Publish the static archive and disable public address resolution, public API mutation, editorial login, and dynamic result routes. Keep the prior dynamic host available only for rollback; do not expose its administrative ports. |
| November 16–18 | Monitor the domain, HTTPS, links and static content. Roll back only for a material static-site failure, not to resume ordinary editing. |
| November 19 | If the static site and verified backups are sound, take a final export, record checksums and destroy the pilot Droplet. Confirm billing has stopped. |
| After certification | Verify the authority's certification, generate a new versioned static build, review it, and publish it. Preserve the prior unofficial source/version privately. |

If results or certification are delayed, that delays a results update—not the
November 16 removal of address lookup and private editorial access from the public
host. The static site can truthfully say that certified results are not yet
available and link directly to the authority.

## Implementation work required before launch

- Create a deterministic static-export command from published, reviewed records.
- Define a result manifest and status vocabulary without inferring certification.
- Add an official-results intake/review path and source-version checks.
- Add privacy-approved first-party aggregate counters, or explicitly launch with
  no usage metrics.
- Select a static host that supports a custom domain and HTTPS without exposing
  the source repository or private artifacts.
- Add public/static and private/backup artifact allowlists and automated secret/
  private-file checks.
- Write and rehearse the cutover, rollback, restore and Droplet-destruction runbook.
- Test the static site without the API/database and confirm all dynamic endpoints
  fail closed after cutover.

No static host, analytics service, DNS change, public deployment or Droplet
destruction is authorized by this plan.
