# REVIEW-0120 — GOV-002 CHANGES REQUIRED

**Reviewed commit:** 2ff9fb09145bcbf777c1153d685b081b86048e23
**Decision:** CHANGES_REQUIRED
**Date:** 2026-07-21

## Findings
1. **CAT-001 left blank is wrong.** REVIEW-0001 explicitly says CAT-001 is superseded by
   REVIEW-0002/CAT-001A. REVIEW-0002 accepts CAT-001A and states it brings CAT-001 into
   conformance. The correct resolution is `SUPERSEDED BY CAT-001A (ACCEPTED)`, not a blank
   and not an inferred ACCEPTED.
2. **REF-001 authority is mis-attributed.** Its row cites REVIEW-0016 / commit
   `5fac3ac20f4c88074207f795aef3b5f7d6078f5b`. The correct authority is **REVIEW-0017**
   and accepted commit `b742e8d2a3cf5239b93a9541aa0013589297cad2`. The REVIEW-0016 /
   5fac3ac attribution must be removed from its row.
3. **AUD-004 authority is mis-attributed.** Its row cites commit `899fb7c8` as an AUD-004
   accepted commit. That commit belongs to the **AUD-002** dependency, not AUD-004. The
   correct authority is `tickets/AUD-004.md` plus **REVIEW-0065**. Remove `899fb7c8` as an
   AUD-004 accepted commit.
4. **Grouped "all others" assertion is insufficient.** The report must contain one explicit
   row per backlog ticket, not a collapsed "all others" line.
5. **Material restrictions in backlog statuses must be preserved:**
   - FX-001: `ACCEPTED - READINESS ONLY; IMPLEMENTATION BLOCKED BY SOURCE AUTHORITY`
   - FUND-001: `ACCEPTED - REVIEW-0093; IMPLEMENTATION BLOCKED BY SOURCE EVIDENCE`
   - Keep existing no-authority / no-implementation qualifiers for other tickets.
6. **GOV-002 Recommendation** should be set to `RECONCILIATION_COMPLETE` after corrections.

## Authorized corrections (COMMIT 2)
- Resolve CAT-001 as `SUPERSEDED BY CAT-001A (ACCEPTED)` in ticket + backlog.
- Correct REF-001 authority to REVIEW-0017 + commit b742e8d2; remove REVIEW-0016/5fac3ac.
- Correct AUD-004 authority to tickets/AUD-004.md + REVIEW-0065; remove 899fb7c8.
- Replace "all others" with one explicit report row per backlog ticket.
- Preserve FX-001 and FUND-001 material-restriction statuses; keep other qualifiers.
- Set GOV-002 Recommendation RECONCILIATION_COMPLETE; return to AWAITING_REVIEW everywhere.
- No production code, tests, architecture, accepted research findings, or historical
  reviews modified.
