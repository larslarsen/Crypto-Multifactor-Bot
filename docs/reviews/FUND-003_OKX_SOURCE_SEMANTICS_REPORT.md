# FUND-003 — OKX Funding Archive Source Semantics Audit Report

**Status:** AWAITING_REVIEW
**Next ticket authorized:** `NONE`
**Next required actor:** Reviewer
**Date:** 2026-07-21

## Recommendation
**NO_IMPLEMENTATION_AUTHORITY**

Four mandatory gates fail closed: historical availability (G01/G06), archive replacement policy (G05),
and licensing/redistribution (G07). Settlement semantics, sign convention, formula type, interval
derivation, and raw lineage are documented.

## Evidence Summary

All evidence captured from `/tmp/opencode/source_recheck_20260721/` on 2026-07-21. SHA-256 hashes
committed in `research/fund_003/EVIDENCE_REGISTER.csv`. Raw payloads preserved outside Git.

## Gate Results

| Gate | Label | Status | Blocking |
|---|---|---|---|
| G01 | fundingTime event/settlement semantics | FAIL | Yes |
| G02 | fundingRate/realizedRate unit and sign | PASS | No |
| G03 | formulaType effective scope and change | PASS | No |
| G04 | interval derivation and variable intervals | PASS | No |
| G05 | archive integrity and replacement policy | FAIL | Yes |
| G06 | publication/backfill availability | FAIL | Yes |
| G07 | licensing/terms | FAIL | Yes |
| G08 | immutable raw lineage | PASS | No |

## Key Findings

### G01 — fundingTime semantics (FAIL)
- `fundingTime` documented as settlement time in Unix milliseconds (e.g. `1784649600000`).
- REST response confirms: "Settlement time, Unix timestamp format in milliseconds".
- **FAIL**: The 2022-05-01 archive object has `Last-Modified: 2026-02-02`, meaning the object was
  replaced after 2022. No proof the 2022 archive was available in 2022. Historical availability
  unproven.

### G02 — fundingRate/realizedRate unit and sign (PASS)
- `fundingRate`: predicted funding rate for upcoming settlement period.
- `realizedRate`: actual settled funding rate.
- Sign convention documented: positive = long pays short; negative = short pays long.
- Both are dimensionless decimal rates (e.g. `-0.0000386532726688`).

### G03 — formulaType (PASS)
- `noRate`: old funding rate formula.
- `withRate`: new funding rate formula.
- REST response for BTC-USDT-SWAP (2026-07-19) shows `formulaType: withRate`.
- Field present in API; transition boundary (April 2025) documented but not directly observed in
  historical archive.

### G04 — Interval derivation (PASS)
- Default 8-hour interval documented.
- Variable intervals (6h/4h/2h/1h) documented for volatile altcoins.
- Confirmed in 2026-07-19 archive: 196 instruments have 4-hour intervals (e.g. 0G-USDT-SWAP).
- Use `fundingTime`/`nextFundingTime` difference to determine actual interval.

### G05 — Archive integrity (FAIL)
- ETag and Content-MD5 present on all archive objects.
- 2022 archive ETag: `9B200F54D2AF3E2045BF1D26A5D48618`, Content-MD5: `myAPVNKvPiBFvx0mpdSGGA==`.
- **FAIL**: Provider replacement policy not established. 2022 object Last-Modified 2026-02-02
  proves replacement occurred; no changelog or version history available.

### G06 — Publication/backfill availability (FAIL)
- Historical endpoint introduced September 2025 per documentation.
- 2022 archive object Last-Modified: 2026-02-02 (replacement, not original publication).
- `exportTime` in API responses equals retrieval time (e.g. `1784676806847`), not publication time.
- **FAIL**: No conservative historical availability bound separate from local retrieval time.

### G07 — Licensing (FAIL)
- OKX API terms restrict Market Data to personal, non-commercial use.
- Redistribution explicitly prohibited.
- **FAIL**: No commercial license established. Internal metadata retention may be permitted under
  fair use but redistribution is prohibited.

### G08 — Immutable raw lineage (PASS)
- All raw payloads preserved at `/tmp/opencode/source_recheck_20260721/`.
- SHA-256 hashes committed in evidence register.
- External paths recorded.
- Provider ETag/Content-MD5 verified against captured objects.

## Recommendation

**NO_IMPLEMENTATION_AUTHORITY** — fail-closed on G01 (historical availability unproven), G05
(replacement policy unestablished), G06 (no publication bound), and G07 (redistribution prohibited).

Even a passing audit cannot authorize realized funding-cashflow, portfolio, CARRY, USD-conversion,
schema, ADR, migration, or production work.
