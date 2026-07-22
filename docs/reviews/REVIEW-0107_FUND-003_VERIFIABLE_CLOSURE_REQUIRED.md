# REVIEW-0107 — FUND-003 VERIFIABLE CLOSURE REQUIRED

**Reviewed commit:** b50d179
**Decision:** CHANGES_REQUIRED
**Next ticket authorized:** NONE
**Date:** 2026-07-21

## Defects Identified

1. **Evidence-register path/hash/size validation failures** — header-file byte sizes were wrong:
   R01H was 1182 (actual 1072), R02H was 1103 (actual 1077), R03H was 1344 (actual 1132),
   R11H was 2079 (actual 1673 in prior capture; replaced entirely), R12H was 418 (actual 1077).
2. **R11 was a 302-redirect-followed 404/agreement page, not a genuine HTTP 200 capture** from the
   direct agreement URL.
3. **Missing official formula announcement** and **BTC transition-boundary archives** (April 24 2025).
4. **Unsourced "September 2025 endpoint introduction" claim** — not present on the landing page;
   no changelog captured to support it.
5. **Semantic errors**: Last-Modified was said to prove replacement; G04 omitted from summary/
   recommendation; G07 framed around redistribution rather than intended internal scope; ambiguity
   not treated as a failure mode.
6. **CURRENT_TASK accepted dependency** listed FEE-001, not FUND-001.
7. **REVIEW-0106 claims** implied POST bodies were captured; they were not.

## Corrective Actions

1. REVIEW-0107 created (this document).
2. All header sizes corrected: R01H 1072, R02H 1077, R03H 1132, R11H 5162 (replaced), R12H 1077.
   Deterministic validator confirms every row: external_path exists, SHA-256 matches, byte size
   matches, registered HTTP status agrees with retained headers.
3. R11 replaced with genuine HTTP 200 capture from
   `https://www.okx.com/en-eu/help/okx-api-agreement` (effective status 200; server emits HTTP 103
   Early-Hints before the 200 body). Exact final URL, body, headers, status, retrieval time, SHA-256,
   and size registered. Old 404/redirect page not used.
4. Formula announcement captured (RFA): `https://www.okx.com/en-eu/help/okx-to-change-the-funding-
   rate-formula-for-perpetual-futures` — states 3 batches from April 10, 2025. BTC transition-boundary
   archives around 2025-04-24 could NOT be acquired (all probed April 2025 dates returned 404); stated
   literally. April 15 archive retained only as a general April-2025 sample, not the BTC boundary.
5. Changelog captured (RCL): `https://www.okx.com/docs-v5/log_en/` (HTTP 200). Its 2025-04-28 entry is
   AWS-domain cessation, not the funding-formula transition. The unsourced "September 2025" claim is
   removed from all records.
6. Semantics corrected: Last-Modified no longer claimed to prove replacement; G04 included in summary
   and final recommendation (blocking); G07 evaluated only against intended internal acquisition and
   metadata retention, failing on ambiguity (not on absence of redistribution rights); redistribution
   noted as outside the gate.
7. CURRENT_TASK accepted dependency corrected to FUND-001.
8. REVIEW-0106 claims reconciled: exact POST request bodies for R08–R10 remain unavailable; register
   states this literally and does not claim capture.
9. Deterministic validator run over every evidence row (path exists, SHA matches, size matches,
   status agrees, no semantic claim sourced from redirect/error page).
10. `check_repo_control.py` PASS; `git diff --check` clean.

## Status

CHANGES_REQUIRED — published as a new corrective commit (not an amend of b50d179). FUND-003 remains
AWAITING_REVIEW; Reviewer next; Next ticket authorized NONE.
