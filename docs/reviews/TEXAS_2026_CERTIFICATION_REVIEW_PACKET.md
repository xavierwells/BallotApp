# Texas 2026 certification review checklist

**Status:** awaiting human transcription review; one reviewer suffices for these official facts  
**Source:** [Texas Secretary of State 2026 Ballot Certification](https://www.sos.state.tx.us/elections/forms/2026-ballot-cert.pdf)  
**Expected SHA-256:** `c13ffb4ebeee389fa9818d47b31f77b4e260ea6e6f5389cb7bf0f36d9b44d87c`  
**Expected size:** 5,919,631 bytes  
**Published:** 2026-08-28

The operator confirmed a successful private download with the exact size and
checksum above. The source file is available at
`data/private/2026-ballot-cert.pdf`; this is download evidence, not editorial
sign-off. Database registration has not yet been confirmed.

This packet is an optional checklist. Use the implemented
[editorial workspace](../EDITORIAL_VERIFICATION_WORKFLOW.md) to record decisions
against source pages and immutable draft revisions. Unreviewed private loading
is allowed; this Markdown file does not authorize canonical import.

## Review targets

| County | Report pages | Staged races | Staged candidates | Manifest |
| --- | ---: | ---: | ---: | --- |
| Bell | 70–75 | 40 | 79 | `data/candidates/texas-2026-general-bell-certification.json` |
| Coryell | 271–275 | 36 | 70 | `data/candidates/texas-2026-general-coryell-certification.json` |
| Lampasas | 783–787 | 32 | 67 | `data/candidates/texas-2026-general-lampasas-certification.json` |

## Reviewer procedure

1. Open the already downloaded private PDF and confirm its checksum. Retrieve
   from the source URL only if the pinned file is unavailable; a replacement
   with different bytes must not be silently substituted.
2. Compare every race title, candidate ballot label, party label, and page number.
3. Confirm that county-specific and precinct-specific contests were not treated as countywide ballot applicability.
4. Record every discrepancy; correct the manifest through review rather than silently accepting it.
5. Save decisions in the workspace for the races actually checked. Xavier can
   review the AI transcription; no second human is required for these basic
   official facts. Partial progress does not sign off the whole packet. The
   fields below can supplement, but never replace, the authenticated audit trail.

## Sign-off

- Reviewer reference:
- Review date:
- County/page scope:
- Reviewed manifest revision or checksum:
- Result: pending
- Discrepancies/corrections:

This review verifies transcription only. It does not assert that every race is
on every voter's ballot and does not replace county sample-ballot verification.
