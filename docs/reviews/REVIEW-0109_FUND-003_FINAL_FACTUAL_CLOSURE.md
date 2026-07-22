# REVIEW-0109 — FUND-003 FINAL FACTUAL CLOSURE

**Reviewed commit:** f5a9a5c567a1675d88bba19044d3c558319ded10
**Decision:** CHANGES_REQUIRED
**Next ticket authorized:** NONE
**Date:** 2026-07-21

## Defects Identified

1. Residual "Last-Modified proves replacement" phrasing remained in the report (G05), decision
   matrix (G05), and okx.md — needed the exact replacement wording.
2. Unregistered HTTP-404 claims (enumerated failed dates) remained in the report (G03/G06),
   decision matrix (G06), okx.md, and R12/RFA register limitations.
3. Mechanism formula in okx.md was inverted: stated "scaled by ÷N"; correct factor is 8/N.
4. RFAH limitation said "announcement dated April 10 2025"; correct: published March 14, 2025,
   rollout began April 10, 2025.
5. FUND-001 described as "source semantics baseline" in CURRENT_TASK and the FUND-003 ticket;
   should be "funding readiness baseline".
6. Report correction chain did not list REVIEW-0108 or REVIEW-0109.

## Corrective Actions

1. REVIEW-0109 created (this document).
2. Every "Last-Modified proves replacement" claim replaced with:
   "Last-Modified dates the current representation but cannot distinguish initial backfill
   from replacement."
   Applied in: FUND-003_OKX_SOURCE_SEMANTICS_REPORT.md (G05), decision_matrix.csv (G05),
   sources/okx.md.
3. All unregistered HTTP-404 claims removed. Stated only:
   "BTC transition-boundary archives around April 24 were not acquired in this audit."
   Applied in: report (G03, G06), decision matrix (G06), source note (okx.md), and
   R12B/RFA register limitations. No enumerations of failed dates remain (none were
   registered with exact 404 bodies/headers).
4. Mechanism formula corrected in sources/okx.md: N is the settlement interval in hours;
   the rate divides by (8 / N), not by N.
5. RFAH limitation corrected: announcement published March 14, 2025; rollout began
   April 10, 2025. RFA body limitation updated to match; R12B limitation updated to
   the "NOT acquired in this audit" wording.
6. FUND-001 description corrected to "funding readiness baseline" in CURRENT_TASK and
   the FUND-003 ticket.
7. Report correction chain updated to include REVIEW-0108 and REVIEW-0109.
8. Re-ran validation:
   - path/SHA-256/byte-size validation: ALL 22 rows valid.
   - final HTTP-status validation: all header rows' registered status present in retained headers.
   - `python3 scripts/check_repo_control.py`: PASS.
   - `git diff --check`: clean.

## Status

CHANGES_REQUIRED — published as a new corrective commit (not an amend of f5a9a5c). FUND-003 remains
AWAITING_REVIEW; Reviewer next; Next ticket authorized NONE.
