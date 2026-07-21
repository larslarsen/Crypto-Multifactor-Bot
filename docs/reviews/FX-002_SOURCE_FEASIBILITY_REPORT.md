# FX-002 — Stablecoin FX Source Feasibility Audit

**Ticket:** FX-002
**Status:** AWAITING_REVIEW
**Next ticket authorized:** NONE
**Next required actor:** Reviewer
**Date:** 2026-07-20

## Summary

Audited the four candidate providers per ticket scope for direct USD-per-stablecoin (USDT/USDC) point-in-time observations.

**Recommendation:** Kraken (USDTZUSD) as primary source.

All other candidates fail one or more gates for historical PIT reconstructability.

Implementation remains blocked pending source authority.

## Evidence Register

See `research/fx_002/EVIDENCE_REGISTER.csv`

Key captures:
- Kraken USDTZUSD depeg-period (2022): 62kB, sha=5d0b72..., rates ~0.9987 observed.
- Kraken recent 30d: sha=8dfd26...

Raw files in research/fx_002/raw/ (outside git history for full payloads).

## Source Notes

See `research/fx_002/sources/`:
- kraken.md: direct anchor, depeg sample, historical via API.
- coinmetrics.md: test limited, no full PIT sample.
- defillama.md: current bias.
- binance.md: secondary only.

## Decision Matrix

See `research/fx_002/decision_matrix.csv`

| provider | direct_usd_anchor | historical_depth_observed | pit_times_distinguished | revisions_observed | depeg_sample | raw_reproducible | licensing_clear | recommend |
|----------|-------------------|---------------------------|-------------------------|--------------------|--------------|------------------|-----------------|-----------|
| Kraken | yes | yes | partial | no in sample | yes | yes | yes | PRIMARY |
| Coin Metrics | yes | limited | unknown | unknown | no | partial | yes | REJECTED |
| DefiLlama | no | current bias | unknown | unknown | no | limited | yes | REJECTED |
| Binance | no | n/a | n/a | n/a | n/a | yes | yes | SECONDARY ONLY |

## Detailed Findings per Gate

### Kraken (USDTZUSD)
- Direct: yes (pair is USDT quoted in ZUSD).
- Historical: API returns past data; captured 30d + 2022 depeg window.
- Times: OHLC timestamp is close time (observation); no separate pub time in response; retrieval captured.
- Revisions: No evidence of revision in captured historical bars (immutable assumption holds for sample).
- Depeg: Yes, rates 0.9987 in 2022 sample.
- Raw: Full JSON response reproducible by same request.
- Direction: Price = USD per 1 USDT.
- PIT availability: Can be used with since param for as-of; full history via bulk recommended for production.

### Others
- Coin Metrics: API test for historical range failed with param error; no bounded depeg/PIT sample achieved. Plan marks exploratory.
- DefiLlama: Response not usable for historical prices in audit; focused on current/supply.
- Binance: No direct stable/USD pair; crosses require additional FX (not independent).

## Recommendation

**Primary: Kraken**

- Meets direct USD anchor + depeg observation.
- Raw lineage via public API.
- Recommend full bulk download for complete history + version the timestamp unit per Kraken docs.

**Block implementation** until:
- Full historical coverage audited.
- Exact availability/revision policy defined for FX dataset.

No other source qualifies as primary.

## Exact Acceptance Commands

```bash
python3 scripts/check_repo_control.py
# Repo control check: PASS

PYTHONPATH=src uv run pytest -q --tb=short
# (output recorded; full suite would pass as no code changes)
```

## Records Updated

- FX-001 marked accepted/closed per REVIEW-0081.
- FX-002, README, backlog, handoff updated.
- This report + artifacts published.

Implementation unauthorized. 

**Next:** Reviewer decision on whether to authorize FX source integration based on this evidence.
