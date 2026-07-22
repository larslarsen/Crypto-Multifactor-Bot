# REVIEW-0115 — REF-003 PROSPECTIVE AUDIT AUTHORIZED

**Authorized ticket:** REF-003
**Auditor:** Jr Dev — Hermes (Hy3:free)
**Date:** 2026-07-21
**Decision:** AUTHORIZE — create and complete REF-003.

## Scope authorized
Bybit prospective instrument-snapshot authority audit only. Historical state
transitions, settled events, announcements, and REF-002 G04/G05 remain blocked and
out of scope.

## Required gates (8)
1. Official legal-document chain and version identity. 2. API Terms applicability vs Platform Terms.
3. Permission for automated public-API acquisition. 4. Permission for internal non-commercial raw snapshot retention.
5. Deterministic instruments-info pagination and request identity. 6. Prospective known-time semantics.
7. No redistribution or commercial-use assumption. 8. Immutable snapshot/version lineage.

## Constraints
- Register exact PDF/API bodies and headers separately (URLs, statuses, hashes, sizes,
  versions, external paths).
- Do NOT use the old unsupported help-page shell as terms evidence.
- Do NOT infer retention permission from general API access.
- A pass authorizes only a later implementation ticket. No collector, code, schema,
  migration, historical reconstruction, factor, portfolio, or live work now.

## Deliverables required
- docs/reviews/REVIEW-0115_REF-003_PROSPECTIVE_AUDIT_AUTHORIZED.md (this file)
- tickets/REF-003.md
- docs/reviews/REF-003_BYBIT_PROSPECTIVE_AUTHORITY_REPORT.md
- research/ref_003/EVIDENCE_REGISTER.csv
- research/ref_003/decision_matrix.csv
- research/ref_003/sources/bybit.md
- matching README, backlog, CURRENT_TASK updates.

## Outcome
REF-003 completed: **NO_AUTHORITY**. State AWAITING_REVIEW; Reviewer next;
Next ticket authorized NONE.
