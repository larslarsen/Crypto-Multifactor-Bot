# REVIEW-0108 — FUND-003 FACTUAL RECONCILIATION REQUIRED

**Reviewed commit:** bdb312c41b8cf34212047d491732f635873ffdc9
**Decision:** CHANGES_REQUIRED
**Next ticket authorized:** NONE
**Date:** 2026-07-21

## Defects Identified

1. `research/fund_003/sources/okx.md` still carried the unsourced "September 2025 introduction"
   claim and an imprecise Last-Modified statement; lacked the RFA capture, BTC-boundary
   unavailability, and the G07 ambiguity for intended internal use.
2. Report/matrix still implied Last-Modified could establish replacement in places, and phrased the
   April-2025 404 as "all probed April 2025 dates" rather than BTC transition-boundary dates
   around April 24.
3. R11B/R11H `http_status` was 103 (the Early-Hints line) rather than the final effective 200.
4. R06B (mechanism article) attribution was conflated with the API docs: mechanism article states
   1h/2h/4h/8h; the API documentation additionally mentions a possible 6h adjustment.
5. Retrieval (acquisition) times in the register read as precise when they are rounded capture
   timestamps, not independently retained precise times — part of G08's failure.

## Corrective Actions

1. REVIEW-0108 created (this document).
2. `research/fund_003/sources/okx.md` updated to match accepted evidence:
   - Removed the September-2025 introduction claim (endpoint introduction date is not stated on the
     landing page).
   - Stated that Last-Modified dates the current representation; it does NOT prove replacement.
   - Recorded that the official formula announcement was captured as RFA.
   - Stated that BTC boundary archives around April 24 were unavailable (all probed BTC
     transition-boundary dates around April 24 returned 404).
   - Recorded the G07 ambiguity for the intended internal research use.
   - Corrected R06B attribution: mechanism article 1h/2h/4h/8h; API docs additionally 6h.
   - Added the retrieval-time caveat (rounded capture timestamps, not independently retained;
     part of G08 failure).
3. Report and decision matrix: every "Last-Modified proves replacement" statement removed
   (negations retained where present).
4. Replaced "all probed April 2025 dates returned 404" with "all probed BTC transition-boundary
   dates around April 24 returned 404" in the report (G03/G06) and decision matrix (G06).
5. R11B and R11H `http_status` set to final effective 200; the preceding HTTP 103 Early Hints
   is mentioned only in the limitation/notes field.
6. R06B attribution corrected in okx.md, report (G04), and decision matrix (G04): mechanism
   article 1h/2h/4h/8h; API documentation additionally mentions possible 6h.
7. Retrieval-time caveat added to G08 rows (R08–R10) and a general note on all rows: registered
   retrieval times are rounded capture timestamps, not independently retained precise times; this
   remains part of G08's failure. No claim of exact local retrieval completion times is made.
8. Re-ran validation:
   - Deterministic external_path/SHA-256/byte-size validation: ALL 22 rows valid.
   - Final non-informational HTTP-status validation: all header rows' registered status present in
     retained headers (R11 now 200, present on line 4 of retained header file).
   - `python3 scripts/check_repo_control.py`: PASS.
   - `git diff --check`: clean.

## Status

CHANGES_REQUIRED — published as a new corrective commit (not an amend of bdb312c). FUND-003 remains
AWAITING_REVIEW; Reviewer next; Next ticket authorized NONE.
