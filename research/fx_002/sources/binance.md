# Binance

**Capture from register (direct symbols):**
- BINANCE-USDTUSD-SYMBOL: https://api.binance.com/api/v3/exchangeInfo?symbol=USDTUSD , 200, sha=568add8a136f0a7b1c5ab03fc13673074ab5ba1e06953fe4048a1eb69a354c6d , size=5161
  baseAsset=USDT, quoteAsset=USD, status=TRADING
  rate_direction: USD per USDT
- BINANCE-USDCUSD-SYMBOL: similar, base=USDC, quote=USD, USD per USDC

**Archive objects:**
- Multiple daily klines archive URLs (e.g. .../USDTUSD-1d-2022-05-01.zip) return 404 NoSuchKey. No objects observed for depeg window or any tested dates.
- No historical depth, no depeg sample (404), no PIT, no revision data from archive.

**Docs:**
- Captured https://binance-docs.github.io/apidocs/spot/en/ (redirect page). No explicit definition of `USD` quote asset as fiat USD located.
- Fiat-anchor semantics: UNKNOWN

**Conclusion for this candidate:**
Historical depth observed: no (no archive objects for symbol).
Direct USD anchor: yes (instrument definition shows quote=USD for base=USDT/USDC).
PIT times: no.
Revisions observed: UNKNOWN.
Depeg sample: no (404 for 2022-05 window).
Raw reproducible: yes (for live symbol; no for archive).
Licensing clear: no.
Fiat semantics: UNKNOWN (no doc found).
Source status: REJECTED (fails historical depth, depeg sample, licensing, and fiat semantics gates).
Recommend: NONE
