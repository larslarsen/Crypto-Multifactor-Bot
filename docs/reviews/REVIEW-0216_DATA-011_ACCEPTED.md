# REVIEW-0216 — DATA-011 ACCEPTED

**Ticket:** DATA-011 — Survivorship-Bound CEX Quality Bar Panel (Binance First)
**Decision:** ACCEPTED (with caveats)
**Reviewer:** Lead Quantitative Finance Researcher/Engineer
**Base commit:** `f93e43f` (+ uncommitted working tree)

## Summary

Survivorship-bound Binance daily bar panel published as PASS canonical dataset `ds_2bf3bf423a0c751e856dad506f12b6d8b4185b01f7408c46d76a9e7eed3f1497`. Name-based disambiguation (`PAPER_BASE_TO_NAME`) fixes false-positive ticker exclusions (SOL/UNI/CRV/OP). All 23 paper symbols backfilled, 0 excluded, 84,470 PASS bars across 2020-01-01 → 2026-07-01. `live_eligible: false`.

## What works

| Item | Evidence |
|------|----------|
| Name disambiguation | `PAPER_BASE_TO_NAME` + exact name match — SOL/UNI/CRV/OP retained |
| Exclusions | `[]` — 23/23 paper symbols kept |
| Real publish | `data_mode: real_asof`, `canonical_dataset_id: ds_2bf3bf…` |
| Quality | `PASS`, 84,470 bars, 2020-01-01 → 2026-07-01 |
| Catalog recon | `resolve_latest` matches pin |
| `live_eligible` | false |
| Dry-run default | safe for accidental runs |
| Repo control | `check_repo_control.py` PASS |

False-positive ticker bug from prior pass is fixed.

## Caveats (accepted as non-blocking)

1. **Does not call `universe_at`** — reimplements death logic by hand. Can drift from UNIVERSE-006. Recommend shared helper later.
2. **Survivorship is coarse** — drop whole symbol if dead before panel start; no bar-level death clip mid-window.
3. **Join is thin** — `cmc_symbols_matched: 4` of 23. Last-write-wins on ticker dict; name filter saves majors. Liquid U50 panel ≈ "no-op graveyard + full backfill."
4. **ARCH-002 not wired** — acceptance item 2 (paper dry-run with binding) deferred. Accept as bar panel only.
5. **Tests** reimplement exclusion; don't hit publish path. PEPE map typo in test (`PEPEUSD`→`PEPEUSD` — no-op).
6. **Not committed** — working tree uncommitted (Jr duty).

## Scope accepted

PASS Binance daily panel for full static 23-map after CMC name-safe filter. Not a true PIT composite universe.

## Evidence artifacts

- `research/sprint_004/43_BOUND_BARS.json` — full report: 23 symbols, 84,470 bars, survivorship join detail
- `scripts/research/build_bound_bars.py`
- `tests/universe/test_bound_bars.py`

## Verification

- `python3 scripts/check_repo_control.py` — PASS

## Next

Next ticket: **NONE** — pending reviewer authorization.
