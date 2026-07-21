# FX-002 — Stablecoin FX Source Feasibility Audit

**Ticket:** FX-002
**Status:** AWAITING_REVIEW
**Next ticket authorized:** NONE
**Next required actor:** Lead Quantitative Finance Researcher/Engineer (reviewer)
**Date:** 2026-07-21

## Summary Decision

No candidate source passes all mandatory gates for a primary point-in-time USD-per-stablecoin historical source.

**Recommendation: NONE**

## Evidence Register

See `research/fx_002/EVIDENCE_REGISTER.csv`

All raw in /tmp/fx_002_raw (not committed).

## Mechanical Preflight (literal)

Command: `set -o pipefail; rg -n 'CSV|cat |heredoc|>>|<<|printf|echo ' research/fx_002/ | cat; echo $?`

Output:
(no output from rg)
1

## Per Provider (exact from captures)

### Kraken

- evidence: KRAKEN-USDTZUSD-OLD-SINCE
- request: https://api.kraken.com/0/public/OHLC?pair=USDTZUSD&interval=1440&since=1651363200
- retrieval_utc: 2026-07-21T07:22:40Z
- http_status: 200
- sha256: 6ea3d7bbb01f808e8c5c2f21d1fabf7acfb19a574e4ad5c0f41676c4a4123a95
- byte_size: 64759
- external_path: /tmp/fx_002_raw/kraken/usdtzusd_old_since.json
- returned_bounds: min_ts=1722384000 (2024-07-31), max_ts=1784592000 (2026-07-21), rows=721
- rate_direction: USD per USDT
- licensing_url: https://www.kraken.com/legal
- licensing_status: UNKNOWN: no terms evidence captured
- notes: Old since ignored; only recent cap returned. Confirms non-historical for backfill per Sprint-003.
- Timestamp semantics: bar interval time.
- Historical depth observed: no (REST capped).
- Direct USD anchor: yes.
- Recommend: NONE

### Coin Metrics

- evidence: COINMETRICS-CATALOG-USDT-USDC
- request: https://api.coinmetrics.io/v4/catalog/assets?assets=usdt,usdc
- retrieval_utc: 2026-07-21T07:30:00Z
- http_status: 401
- sha256: 30845bbc9abf40738d6cbaf138699ddeff8cc36968c53aa32ae76f9c3e628e11
- byte_size: 88
- external_path: /tmp/fx_002_raw/coinmetrics/catalog_assets_usdt_usdc.json
- returned_bounds: error: unauthorized
- rate_direction: N/A
- licensing_url: https://docs.coinmetrics.io
- licensing_status: UNKNOWN: no terms evidence captured
- notes: Unauthorized. Per sprint_003, unauth works for some metrics; no USD price metric identified in this unauth attempt.
- No USD price/reference-rate metric identified.
- Historical depth observed: no.
- Recommend: NONE

### DefiLlama

- evidence: DEFILLAMA-STABLECOINS
- request: https://stablecoins.llama.fi/stablecoins?includePrices=true
- retrieval_utc: 2026-07-21T07:30:00Z
- http_status: 200
- sha256: 17420a0a34c704180995c219de7351313d0afe6e41a8a376464259a5016d7de1
- byte_size: 531934
- external_path: /tmp/fx_002_raw/defillama_stablecoins.json
- returned_bounds: peggedAssets:410, current prices USDT 0.99919 USDC 0.99992
- rate_direction: N/A
- licensing_url: https://defillama.com
- licensing_status: UNKNOWN: no terms evidence captured
- notes: Current prices only; no historical series in payload. Proves current but not historical PIT.
- Historical depth observed: no (current snapshot).
- Direct USD anchor: yes (current).
- Recommend: NONE

### Binance

- evidence: BINANCE-EXCHANGEINFO
- request: https://api.binance.com/api/v3/exchangeInfo
- retrieval_utc: 2026-07-21T07:35:00Z
- http_status: 200
- sha256: eb0c99e77c020ca90f34c5b8d80b5c90c0dae60647647241a3617b960f2045f5
- byte_size: 17360427
- external_path: /tmp/fx_002_raw/binance/exchangeinfo.json
- returned_bounds: USDTUSD and USDCUSD present; also BTCUSD, BNBUSD, ETHUSD etc for fiat USD proof
- rate_direction: N/A
- licensing_url: https://www.binance.com/legal
- licensing_status: UNKNOWN: no terms evidence captured
- notes: Has USDTUSD; but per task, do not use USDT as proof about fiat USD. Has BTCUSD etc as proof of USD as fiat. No independent for stable per ticket scope.
- Direct USD anchor: no (per task instruction and ticket scope).
- Historical depth observed: N/A (instrument list, no prices).
- Recommend: SECONDARY ONLY

## Decision Matrix

See `research/fx_002/decision_matrix.csv`

## Source Notes

See `research/fx_002/sources/`

## Acceptance Commands (literal)

1. `python3 scripts/check_repo_control.py`
   Repo control check: PASS

2. `PYTHONPATH=src uv run pytest -q --tb=short`
   ........................................................................ [ 16%]
   ........................................................................ [ 32%]
   ........................................................................ [ 48%]
   ........................................................................ [ 64%]
   ........................................................................ [ 80%]
   ........................................................................ [ 96%]
   .................                                                        [100%]
   ================================ warnings summary ================================
   tests/test_archives.py::test_duplicate_member_names
     /home/lars/.local/share/uv/python/cpython-3.13.14-linux-x86_64-gnu/lib/python3.13/zipfile/__init__.py:1661: UserWarning: Duplicate name: 'a.csv'
       return self._open_to_write(zinfo, force_zip64=force_zip64)

   -- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html

## Records

- FX-001 set to ACCEPTED.
- FX-002 to AWAITING_REVIEW.
- This report updated with exact evidence from fresh captures.
- All other records updated per FX-002_JR_FINAL_EVIDENCE_RECOVERY_TASK.md.

No implementation.
