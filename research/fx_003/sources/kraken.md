# Source note — Kraken (FX-003, corrected under REVIEW-0112)

Audit target: `master_q4/USDTUSD_1440.csv` member of `Kraken_OHLCVT.zip`
hosted on Google Drive. Actual file ID: `1ptNqWYidLkhb2VAKuLCxmp2OXEfGO-AP`
(confirmed present in the retained Google Drive view HTML).

## Verified facts (corrected)
- Pair `USDTUSD` = **USD per USDT**. Col4 (close) first 0.9991, last 0.99848.
- **Headerless** CSV, **3,200** daily (24h) rows. Range **2017-03-29 → 2025-12-31**.
  Column layout: `unix_seconds, open, high, low, close, volume_base, count`.
- May 12 2022 depeg bar: O=.9953 H=.9989 L=.92 C=.9971 (daily resolution).
- Bar timestamps Unix seconds aligned to **00:00:00 UTC** (col0 = bar open time).
- ZIP member integrity: CRC-32 `0x32280a6e` matches central directory; compressed
  (76,401) / uncompressed (201,200) sizes match; inflated SHA-256 `9dafa48...`.
- Local file header is **88 bytes** (30 + 26 filename + 32 extra). Captured range
  `6080252262-6080252461` = 88-byte header + **112 compressed bytes**; compressed
  data starts at **6080252350**. Central-directory `offset` = `0xFFFFFFFF` (ZIP64),
  real offset in ZIP64 extra (not captured).
- Archive object Last-Modified: **2026-01-24**. Captures 2026-07-21. All archive
  captures HTTP 206 (ranged) / 200 (view/support/terms). Six header rows carry
  Last-Modified: R01H/R02H/R03H/R04H = 2026-01-24; R06H = 2026-07-21; R08H = 2026-07-21.
  R05H (view) has no Last-Modified.

## Failed / unknown (fail-closed)
- **G03 bar semantics**: 24h UTC-aligned confirmed, but no header row / tz doc in
  archive; bar-time vs publication-time ambiguity not fully resolved.
- **G04 times**: Last-Modified is object date, not data-end or bar time; view page
  has no LM; point-in-time availability of historical rows not pinned.
- **G05 vintages/correction**: central dir + quarterly folder (Q1-2023..Q1-2026)
  captured, but no published correction/replacement policy; ZIP CRC ≠ historical immutability.
- **G07 licensing conflict**: support page permits "use in code / conversion"; EEA Terms
  restrict copying and automated extraction. Unresolved => fail-closed.
- **G08 lineage**: member reproducible via exact byte-range GET + retained headers;
  Google Drive warning/confirmation flow captured. Whole-archive SHA not captured.

## What was NOT done
- No REST backfill used. No "fair use" licensing asserted. No code/schema/normalizer.
- No claim of availability year from Last-Modified. Ranged member NOT treated as
  complete-archive SHA-256.
