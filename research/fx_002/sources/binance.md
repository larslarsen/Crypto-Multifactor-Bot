# Binance

**Capture from register:**
- evidence_id: BINANCE-EXCHANGEINFO
- request_url: https://api.binance.com/api/v3/exchangeInfo
- retrieval_utc: 2026-07-21T07:35:00Z (approx)
- http_status: 200
- sha256: eb0c99e77c020ca90f34c5b8d80b5c90c0dae60647647241a3617b960f2045f5
- byte_size: 17360427
- external_path: /tmp/fx_002_raw/binance/exchangeinfo.json
- returned_bounds: USDTUSD and USDCUSD present; also BTCUSD, BNBUSD, ETHUSD etc for fiat USD proof
- rate_direction: N/A
- licensing_url: https://www.binance.com/legal
- licensing_status: UNKNOWN: no terms evidence captured
- notes: Has USDTUSD; but per task, do not use USDT as proof about fiat USD. Has BTCUSD etc as proof of USD as fiat. No independent for stable per ticket scope.

**Timestamp semantics:**
The exchangeInfo is current instrument list. No historical price data here.

**Conclusion for this candidate:**
Historical depth: no.
Direct USD anchor: no (per ticket: stablecoin cross-pairs as secondary only; do not use USDT/USDC as proof of fiat USD).
PIT times: no.
Revisions: UNKNOWN.
Depeg sample: no.
Raw reproducible: yes.
Licensing clear: no.
Source status: REJECTED (secondary only per FX-002 ticket; fails primary direct USD anchor gate for stablecoin).
