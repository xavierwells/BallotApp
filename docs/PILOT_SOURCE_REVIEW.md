# Copperas Cove pilot source-review research

**Research date:** 2026-08-20  
**Decision status:** research draft only — no registry entry is approved by
this document.

This record supports the source-registry workflow. It is not legal advice or a
license determination. A government source is authoritative for election
facts, but that does not by itself grant permission to copy, retain, automate
against, or redistribute its content.

## Interim rule

All six entries remain `pending_review` for content rights, with automated
monitoring disabled. The initial launch assigns the narrower
`direct_link_manual_check` scope: use a direct source link and manually
inspect the page, but do not download content into the document store, expose
a public copy, scrape, or schedule automated requests.

If a source is ultimately accepted, the project policy is to retain the
accepted artifact privately as provenance evidence. That policy does not
override source terms: public presentation remains `metadata_only` unless the
review finds explicit public-display or redistribution rights.

## Research matrix

| Authority / source | Ownership and current-use evidence | Terms or rights evidence found | Draft disposition |
| --- | --- | --- | --- |
| City of Copperas Cove / Election Information | The page is in the City's City Secretary section and publishes 2026 election notices and candidate materials. | A City [privacy policy](https://www.copperascovetx.gov/site/privacy) was found. It describes site-visitor information, not a content-reuse license. The election page links to Copyright Notices in its footer, but this research did not establish reuse permission. | Keep pending. Direct link and manual inspection only. Ask the City Secretary or City legal contact about private retention, republication of notices/PDFs, and any permitted request cadence. |
| Coryell County / Elections | The [Elections page](https://coryellcountytax.com/Elections/) is branded as the Coryell County Tax Office and publishes official election notices, sample-ballot links, and 2026 dates. | No site-wide reuse, API, bot, or rate-limit terms were located in this review. | Keep pending. Do not infer rights from the official domain or public-record status. Request written confirmation covering retained artifacts and automated access. |
| Bell County / Office of Elections Administration | The [Office of Elections Administration page](https://www.bellcountytx.com/departments/elections/index.php) is on Bell County's official domain, identifies the department, and provides ballots, notices, locations, and election dates. | The page supports ordinary sharing/linking but the site's linked disclaimer could not be retrieved during this review; no content-reuse or automation permission was established. | Keep pending. Direct link and manual inspection only; review the current disclaimer with the County before any copying or automation. |
| Lampasas County / Elections Office | The [Elections Office page](https://www.co.lampasas.tx.us/page/lampasas.testpage2) identifies county election staff, official notices, and current election information. | The page contains a county copyright notice. No explicit reuse license, robot policy, or automated-access permission was found. | Keep pending. Treat content as copyrighted unless the County provides terms or written permission. |
| Copperas Cove ISD / Election 2026 | The [Election 2026 page](https://www.ccisd.com/page/election-2026) is on the district's domain and identifies Copperas Cove ISD. | Its footer states “Copyright © 2026 Copperas Cove ISD. All rights reserved.” No public reuse or automation terms were found. | Keep pending. Do not retain or republish page/document content without specific permission; a plain authoritative link is the only currently defensible public use. |
| Texas Secretary of State, Elections Division / Texas Elections | The [Texas Elections site](https://www.sos.state.tx.us/elections/index.shtml) is the official state Elections Division site. | The [SOS Web Site Link Policy](https://www.sos.state.tx.us/linkpolicy.shtml) says advance permission is not required to link, requires a full forward link, prohibits framing or presenting SOS content as the linker's own, and warns that subpages may change without notice. It does **not** grant content-reuse, retention, scraping, or automated-monitoring rights. | Candidate for a narrowly scoped `metadata_only` link review only. Keep pending until the project records the reviewed policy and decides whether any private retention or automated monitoring is separately authorized. |

## Required reviewer determinations

For each source, record the fields required by `authority_source_registry`:

1. A current terms/license URL or written permission reference.
2. Whether accessing the page or documents has any charge, registration, or
   rate limit.
3. Whether the project may privately retain a fetched or manually supplied
   artifact as provenance evidence.
4. Required citation/attribution language.
5. Whether public excerpts, public copies, or extracted facts are permitted.
6. Whether automated availability/change checks are permitted, and their safe
   request cadence.

Only then should an operator use `python -m app.cli.review_source` to record a
decision. Approving a source for ordinary linking does not automatically
approve private document retention or automation; the relevant review fields
must state those limits explicitly.

## Sources consulted

- [City of Copperas Cove Election Information](https://www.copperascovetx.gov/188/Election-Information)
- [City of Copperas Cove Privacy Policy](https://www.copperascovetx.gov/site/privacy)
- [Coryell County Tax Office Elections](https://coryellcountytax.com/Elections/)
- [Bell County Office of Elections Administration](https://www.bellcountytx.com/departments/elections/index.php)
- [Lampasas County Elections Office](https://www.co.lampasas.tx.us/page/lampasas.testpage2)
- [Copperas Cove ISD Election 2026](https://www.ccisd.com/page/election-2026)
- [Texas Elections](https://www.sos.state.tx.us/elections/index.shtml)
- [Texas Secretary of State Web Site Link Policy](https://www.sos.state.tx.us/linkpolicy.shtml)
