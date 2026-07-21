# Coin Metrics USDT USDC

**Capture from register:**
- evidence_id: COINMETRICS-CATALOG-USDT-USDC
- request_url: https://api.coinmetrics.io/v4/catalog/assets?assets=usdt,usdc
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

**Per sprint_003:**
Unauth catalog works for supply metrics like SplyCur.
No USD price/reference-rate metric identified in this unauth catalog request.

**Conclusion:**
No candidate USD price metric found in unauth catalog.
Source status: REJECTED.
