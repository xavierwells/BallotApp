# Provenance-first data model

This is the required first migration boundary, before any candidate, proposition, or ballot data is persisted. The implementation should use PostgreSQL migrations (Alembic is the preferred migration tool, subject to normal dependency approval).

## Minimum tables

```text
documents
  └── source_claims
        ├── candidates
        ├── ballot_items
        └── propositions

elections
  └── ballot_versions
        └── ballot_items

verification_events
```

| Table | Purpose | Required audit fields |
| --- | --- | --- |
| `documents` | Original authoritative/public documents and retrieval metadata | source URL, publisher, retrieved at, document date, checksum |
| `source_claims` | A single publishable factual assertion or attributed statement | claim text, claim type, source/document/page, status, confidence |
| `verification_events` | Independent verification and correction history | verifier role, action, timestamp, before/after values |
| `elections` | Election authority and event | authority, election date, jurisdiction |
| `ballot_versions` | A time-bounded official ballot style | official source, retrieved at, publication/verification status |
| `ballot_items` | Ordered entries on one ballot version | race/proposition type, sequence, source citation |
| `candidates` | A person running in a specific race | canonical name, office/race reference, candidate-status source |

## Non-negotiable fields

- No published candidate fact is an unlinked column value. It must be represented by at least one `source_claim`.
- Claim types distinguish verified fact, candidate statement, editorial analysis, and community tip.
- Documents and ballot versions are immutable after publication; corrections create a superseding revision and `verification_event`.
- Claims include editorial status (`draft`, `needs_review`, `verified`, `published`, `retracted`), confidence, and a visible “last verified” time.
- Candidate responses are source documents/claims, not automatically verified facts.

The physical schema may evolve, but these relationships and audit properties may not be bypassed for speed.
