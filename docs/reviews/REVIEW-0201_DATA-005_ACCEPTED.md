# REVIEW-0201 — DATA-005 ACCEPTED (with operational caveats)

**Ticket:** DATA-005 — Quality-Cleared Bars for Frozen TSMOM Candidate Path  
**Decision:** ACCEPTED  
**Reviewer:** Lead Quantitative Finance Researcher/Engineer  
**Date:** 2026-07-23  
**Commit:** `518cb0f`

## Summary

Approach **A**: BAR-001 transform **v6** adds native **`1d`** to daily-eligible intervals. New canonical dataset is **`quality_status: PASS`**. Ticket scope met. **No LIVE.**

## Evidence

| Field | Value |
|-------|--------|
| Approach | A (native 1d daily eligibility) |
| Old dataset | `ds_a17651d5…` **REJECTED** (v5) |
| **New dataset** | `ds_0cb6415f…` **PASS** (v6) |
| Span | 2024-01-01 → 2026-07-23 (~30.7m) |
| Layout | intraday 9350 + daily 9350; quarantine 0 |
| `live_eligible` | false |
| Test | `test_native_daily_1d_source_promotes_pass` |

## Accepted

- `src/cryptofactors/market/bars.py` v6 + `1d` in `_DAILY_RESAMPLE_INTERVALS`
- Report + runner; frozen-config note (no TSMOM re-tune)

## Binding caveats

1. **Daily flags say `resampled_from_intraday`** even for native 1d identity promotion — naming is slightly misleading; economics are 1d→1d complete-day promotion. Non-blocking.
2. **`created_at` is epoch (`1970-01-01`) for all catalog rows** → `resolve_latest_by_type("market_bars")` orders by `dataset_id` and still returns the **old REJECTED** `ds_a176…`, **not** the new PASS set.
3. **Any consumer must pin** `ds_0cb6415fa79119bf5317c124e9da2f0d4953b9a8d119aae45e2589ba716c5aaa` until resolve/latest is fixed.
4. Frozen `tsmom_14_3` paper (+16.7%) was on **REJECTED** bars; must **re-validate on PASS dataset** before any LIVE discussion.
5. Double partition (intraday+daily both 1d) is OK if as-of readers are explicit; document which partition research uses.

## LIVE policy

**No LIVE.** Quality PASS exists but is not the default resolve target; frozen strategy not yet re-proven on PASS bars.
