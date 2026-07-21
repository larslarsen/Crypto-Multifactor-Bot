# Coin Metrics - USDT/USDC (source note - corrected)

**Per accepted sprint_003/sources/coin_metrics.md:**
- Unauthenticated Community catalog and timeseries work for supported metrics (e.g. SplyCur on usdt).
- Catalog /catalog/asset-metrics no-param returns data.
- Timeseries uses date windows + next_page_key, rejects limit.
- For supply metrics, community:true for usdt.

**For USD price/reference rate:**
- Catalog attempt for asset-metrics on usdt showed no direct "price_usd" in unauth context or not confirmed for stable USD reference.
- Timeseries for price_usd on usdt returned unauthorized in current test.
- No qualifying public unauth USD-per-stable metric catalog entry confirmed for historical PIT in this audit.
- Sprint focused on supply, not price for stables.

**Gates:**
- direct_usd_anchor: UNKNOWN (no metric found)
- historical: no
- etc: NOT_EVALUATED or no
- recommend: NONE

**Evidence:** Cite sprint_003 for unauth behavior; current attempts confirm no easy USD price for FX.

