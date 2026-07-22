# FX-003 — Kraken Bulk Stablecoin FX Source Semantics Audit Report

**Status:** AWAITING_REVIEW
**Recommendation:** NO_PRIMARY_SOURCE_AUTHORITY
**Next ticket authorized:** `NONE`
**Next required actor:** Reviewer
**Date:** 2026-07-21 (audited under REVIEW-0111)
**Auditor:** Jr Dev — Hermes (Hy3:free)

## Scope
Source-semantics audit of one archive member only:
`master_q4/USDTUSD_1440.csv` inside `Kraken_OHLCVT.zip`
(Google Drive, 7,885,068,519 bytes, 24,056 members).
No code, schema, normalizer, factor, portfolio, or live work.

## Recommendation: NO_PRIMARY_SOURCE_AUTHORITY
Fail-closed. Blocking gates: **G02 (partial), G05 (unknown), G06 (partial), G07 (FAIL), G08 (partial)**.
G01 (direction) and G03 (timestamps) PASS; G04 passes only within its stated limitation.

## Key findings
- **Direction (G01 PASS):** `USDTUSD` = USD per USDT; col4 close ≈ 0.999. Unambiguous.
- **Depth + depeg (G02 FAIL-PARTIAL):** 3,199 daily rows 2017-03-30 → 2025-12-31.
  May 9-15 2022 window present (7 daily bars, closes 0.9953-0.9997) but the intraday
  sub-$0.95 trough is NOT resolvable at daily resolution. Event depth under-resolved.
- **Timestamps (G03 PASS):** Unix seconds aligned to 00:00:00 UTC; col0 = bar open time.
  Bar time is NOT publication time.
- **Times (G04 PASS-with-limit):** object Last-Modified 2026-01-24 (not data-end, not bar time).
- **Vintages/correction (G05 FAIL-UNKNOWN):** no published correction/replacement policy;
  ZIP CRC proves current-member bytes only, not historical immutability.
- **Integrity (G06 PASS-PARTIAL):** member CRC-32 / comp / uncomp match central directory;
  complete-archive SHA-256 NOT captured. A ranged member is NOT the complete-archive SHA-256.
- **Licensing (G07 FAIL):** Google Drive host; Kraken EE/A Terms lack an explicit
  bulk-data redistribution or API-commercial-use clause. Fail-closed.
- **Lineage (G08 PASS-PARTIAL):** member reproducible via exact byte-range GET + retained
  headers/bodies; whole-archive byte-range/SHA not captured (ZIP64 offset=0xFFFFFFFF).

## Decision matrix
See `research/fx_003/decision_matrix.csv` (gates G01-G08).

## Evidence register
See `research/fx_003/EVIDENCE_REGISTER.csv` (12 rows: bodies + headers registered
separately with exact URLs, statuses, hashes, sizes, external paths).

## Validation performed
- path / SHA-256 / size for all 12 rows: **valid**.
- final HTTP status present in retained headers for all 7 header rows: **valid**
  (R01H/R02H/R03H/R04H = 206; R05H/R06H = 200).
- ZIP member CRC-32 / comp / uncomp match central directory: **valid**.
- `python3 scripts/check_repo_control.py`: **PASS**.
- `git diff --check`: **clean** (0 CR bytes in register).

## Note
This audit does not assert availability year, does not use REST for backfill, does not
claim "fair use" licensing, and does not treat a ranged member as the complete-archive SHA-256.
