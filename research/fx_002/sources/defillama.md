# DefiLlama

**Capture from register:**
- evidence_id: DEFILLAMA-STABLECOINS
- request_url: https://stablecoins.llama.fi/stablecoins?includePrices=true
- retrieval_utc: 2026-07-21T07:30:00Z
- http_status: 200
- sha256: 17420a0a34c704180995c219de7351313d0afe6e41a8a376464259a5016d7de1
- byte_size: 531934
- external_path: /tmp/fx_002_raw/defillama_stablecoins.json
- returned_bounds: peggedAssets:410, current prices USDT 0.99919 USDC 0.99992
- rate_direction: NOT_APPLICABLE: current snapshot was rejected before historical rate use
- licensing_url: https://defillama.com
- licensing_status: UNKNOWN: no terms evidence captured
- notes: Current snapshot only; no historical series or PIT timestamps in payload.

**Conclusion:**
The payload is current snapshot. Does not prove historical USD-per-stablecoin prices or PIT.
Source status: REJECTED (fails historical price gate).
