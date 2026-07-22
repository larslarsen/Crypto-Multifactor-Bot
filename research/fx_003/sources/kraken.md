# Source note — Kraken (FX-003, corrected under REVIEW-0111)

Audit target: `master_q4/USDTUSD_1440.csv` member of `Kraken_OHLCVT.zip`
hosted on Google Drive (drive.usercontent.google.com, 7,885,068,519 bytes, 24,056 members).

## Verified facts
- Pair `USDTUSD` = **USD per USDT**. Col4 (close) ≈ 0.999 confirm 1 USDT ≈ $0.999.
- 3,199 daily rows. Range **2017-03-30 → 2025-12-31**. Column layout:
  `unix_seconds, open, high, low, close, volume_base, count`.
- Bar timestamps are Unix seconds aligned to **00:00:00 UTC** (col0 = bar open time).
- ZIP member integrity verified: CRC-32 `0x32280a6e` in central directory equals
  CRC-32 of inflated bytes; compressed (76,401) and uncompressed (201,200) sizes match.
- Local file header uses a data descriptor (crc/size fields zeroed); authoritative
  CRC/size live in the central directory.
- Archive object Last-Modified: **2026-01-24** (object date, NOT data-end 2025-12-31,
  NOT bar time). Captures 2026-07-21. All captures HTTP 206 (ranged) / 200 (view/terms).
- Central-directory `offset` for this member = `0xFFFFFFFF` (ZIP64 marker); the real
  local-header offset lives in the ZIP64 extra field, which was not captured.

## Failed / unknown (fail-closed)
- **Depeg depth**: May 9-15 2022 daily window present (closes 0.9953-0.9997) but the
  intraday sub-$0.95 trough is NOT resolvable at daily (1440-min) resolution.
- **Correction/replacement policy**: no published policy for the bulk archive; ZIP CRC
  proves current-member bytes only, not historical immutability.
- **Complete-archive integrity**: only a ranged member was captured; the full-archive
  SHA-256 was NOT computed. A ranged member must NOT be treated as the complete-archive SHA-256.
- **Licensing**: hosted on Google Drive; Kraken EE/A Terms contain no explicit bulk-data
  redistribution or API-commercial-use clause. Fail-closed on internal-use permission.
- **Reproducible lineage**: member reproducible via exact byte-range GET + retained
  headers/bodies; whole-archive byte-range/SHA not captured.

## What was NOT done
- No REST backfill used. No "fair use" licensing asserted. No code/schema/normalizer written.
- No claim of 2017 (or any) availability from Last-Modified.
