# Coin Metrics - USDT price (source note)

**Tested:**
- Attempt: https://api.coinmetrics.io/v4/timeseries/asset-metrics?assets=usdt&metrics=price_usd&start_time=2022-05-01&end_time=2022-05-10
- retrieval: (current)
- Result: HTTP 401 unauthorized. "Requested resource requires authorization."

**Catalog check:**
- Attempt to list metrics for usdt failed without auth.

**Per repo 02_DATA_SOURCE_PLAN.md:** CONDITIONAL — EXPLORATORY_PHASE2. Use only confirmed available under Community.

**Gates:**
- Direct USD: potentially yes (price_usd metric if available)
- But no public access without key; no bounded historical sample captured.
- No depeg coverage tested.

**Conclusion:** Rejected. No free public historical PIT confirmed.

