# Coin Metrics USDT USDC

**Capture from register:**
- evidence_id: COINMETRICS-CATALOG-ASSET-METRICS-USDT-USDC
- request_url: https://api.coinmetrics.io/v4/catalog/asset-metrics
- retrieval_utc: 2026-07-21T08:00:00Z
- http_status: 401
- sha256: 30845bbc9abf40738d6cbaf138699ddeff8cc36968c53aa32ae76f9c3e628e11
- byte_size: 88
- external_path: /tmp/fx_002_raw/coinmetrics/catalog_asset_metrics.json
- returned_bounds: error: unauthorized
- rate_direction: N/A
- licensing_url: https://docs.coinmetrics.io
- licensing_status: UNKNOWN: no terms evidence captured
- notes: Unauthorized for asset-metrics catalog (not /catalog/assets). No USD price/reference-rate metric identified.

**Per sprint_003:**
Unauth catalog works for supply metrics like SplyCur.
No USD price/reference-rate metric identified in asset-metrics catalog request (unauthorized).

**Conclusion:**
No candidate USD price metric found in unauth asset-metrics catalog.
Source status: REJECTED.
