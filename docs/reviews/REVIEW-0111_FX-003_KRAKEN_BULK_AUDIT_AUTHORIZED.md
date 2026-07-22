# REVIEW-0111 — FX-003 KRAKEN BULK AUDIT AUTHORIZED

**Authorized ticket:** FX-003
**Auditor:** Jr Dev — Hermes (Hy3:free)
**Date:** 2026-07-21
**Decision:** AUTHORIZE — create and complete FX-003.

## Reason
FX-002 and `docs/architecture/02_DATA_SOURCE_PLAN.md` deferred Kraken only until bulk
acquisition succeeded. It now succeeds (retained captures under
`/tmp/opencode/source_recheck_20260721/`).

## Scope authorized
Audit only Kraken's complete OHLCVT archive member `master_q4/USDTUSD_1440.csv`.

## Required gates (8)
1. USD-per-USDT direction. 2. Historical depth + May-2022 depeg coverage.
3. Bar timestamp semantics. 4. Publication/acquisition/availability times.
5. Archive vintages + correction/replacement behavior. 6. Current-byte/member integrity.
7. Internal acquisition/metadata-retention permission. 8. Exact reproducible raw lineage.

## Fail-closed rules
Do not treat bar time as publication time, Last-Modified as proof of replacement, ZIP CRC
as historical immutability, a ranged member as the complete-archive SHA-256, or a ranged
backfill / "fair use" for licensing. No REST backfill.

## Deliverables required
- docs/reviews/REVIEW-0111_FX-003_KRAKEN_BULK_AUDIT_AUTHORIZED.md (this file)
- tickets/FX-003.md
- docs/reviews/FX-003_KRAKEN_BULK_SOURCE_SEMANTICS_REPORT.md
- research/fx_003/EVIDENCE_REGISTER.csv
- research/fx_003/decision_matrix.csv
- research/fx_003/sources/kraken.md
- matching README, backlog, CURRENT_TASK updates.

## Outcome
FX-003 completed: **NO_PRIMARY_SOURCE_AUTHORITY**. State AWAITING_REVIEW; Reviewer next;
Next ticket authorized NONE.
