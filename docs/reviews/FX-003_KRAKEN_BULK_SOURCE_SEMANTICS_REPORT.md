# FX-003 — Kraken Bulk Stablecoin FX Source Semantics Audit Report

**Status:** AWAITING_REVIEW
**Recommendation:** NO_PRIMARY_SOURCE_AUTHORITY
**Next ticket authorized:** `NONE`
**Next required actor:** Reviewer
**Date:** 2026-07-21 (audited under REVIEW-0111; corrected under REVIEW-0112)
**Auditor:** Jr Dev — Hermes (Hy3:free)

## Scope
Source-semantics audit of one archive member only:
`master_q4/USDTUSD_1440.csv` inside `Kraken_OHLCVT.zip`
(Google Drive, file ID `1ptNqWYidLkhb2VAKuLCxmp2OXEfGO-AP`, 7,885,068,519 bytes).
No code, schema, normalizer, factor, portfolio, or live work.

## Recommendation: NO_PRIMARY_SOURCE_AUTHORITY
Fail-closed. Blocking gates: **G03, G04, G05, G07, G08**.
G01 (direction) and G02 (depth/depeg) PASS; G06 (member integrity) PASS.

## Key findings (corrected REVIEW-0112)
- **Direction (G01 PASS):** `USDTUSD` = USD per USDT; col4 close ≈ 0.9991. Unambiguous.
- **Depth + depeg (G02 PASS):** **headerless** CSV, **3,200** daily (24h) rows
  2017-03-29 → 2025-12-31. May 12 2022 depeg bar O=.9953 H=.9989 L=.92 C=.9971.
  Full depeg window covered at daily resolution.
- **Timestamps (G03 FAIL-PARTIAL):** Column 0 is an observed Unix-second OHLC interval
  timestamp aligned to 00:00 UTC. Provider evidence does not establish interval-start
  versus interval-end semantics. FAIL-PARTIAL.
- **Times (G04 FAIL-PARTIAL):** object Last-Modified 2026-01-24 (not data-end, not bar
  time); view page has no Last-Modified; support/terms pages 2026-07-21. Point-in-time
  availability of historical rows not pinned.
- **Vintages/correction (G05 FAIL-PARTIAL):** central dir + quarterly folder
  (Q1-2023..Q1-2026) captured; no published correction/replacement policy;
  ZIP CRC proves current-member bytes only, not historical immutability.
- **Integrity (G06 PASS):** member CRC-32 / comp / uncomp match central directory;
  inflated SHA-256 `9dafa48...` computed. Complete-archive SHA-256 NOT captured.
- **Licensing (G07 FAIL-CONFLICT):** support page permits "use in code / conversion";
  EEA Terms restrict copying and automated extraction; no explicit bulk-redistribution
  grant. Unresolved conflict => fail-closed.
- **Lineage (G08 FAIL-PARTIAL):** member reproducible via exact byte-range GET + retained
  headers; Google Drive warning/confirmation (virus-scan) page captured (R05B), but the
  exact warning/confirmation request-flow parameters (e.g. confirm token) were NOT
  retained. Whole-archive byte-range/SHA not captured (ZIP64 offset=0xFFFFFFFF).

## ZIP64 facts (corrected)
Local file header = **88 bytes** (30 + 26 filename + 32 extra). Captured range
`6080252262-6080252461` = 88-byte header + **112 compressed bytes**; compressed data
starts at **6080252350**. R02's 200 bytes = header + 112 compressed bytes.
The central-directory **32-bit offset field = `0xFFFFFFFF`** (ZIP64 marker);
the **ZIP64 extra field (0x0001) was captured** and carries the **actual
local-header offset = 6080252262**.

## Decision matrix
See `research/fx_003/decision_matrix.csv` (gates G01-G08).

## Evidence register
See `research/fx_003/EVIDENCE_REGISTER.csv` (16 evidence rows: bodies + headers
registered separately with exact URLs — actual file ID `1ptNqWYidLkhb2VAKuLCxmp2OXEfGO-AP`
— statuses, hashes, sizes, external paths; warning/confirmation and quarterly-folder
rows added).

## Validation performed
- path / SHA-256 / size for all 16 evidence rows: **valid**.
- final HTTP status present in retained headers for all **8 header rows** (R01H/R02H/R03H/R04H = 206; R05H/R06H/R07H/R08H = 200): **valid**.
- inflated member SHA-256 / CRC-32 / rows (3,200) / bounds: **valid**.
- `python3 scripts/check_repo_control.py`: **PASS**.
- `git diff --check`: **clean** (0 CR bytes in register).

## Note
This audit does not assert availability year, does not use REST for backfill, does not
claim "fair use" licensing, and does not treat a ranged member as the complete-archive SHA-256.
