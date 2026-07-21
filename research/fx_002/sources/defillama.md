# DefiLlama (source note - corrected)

**Correct endpoint per sprint_003:** https://stablecoins.llama.fi/stablecoins?includePrices=true

**Capture:**
- retrieval: 2026-07-21
- sha: 17420a0a34c704180995c219de7351313d0afe6e41a8a376464259a5016d7de1
- size: 531934
- external: /tmp/fx_002_raw/defillama_stablecoins.json
- payload: peggedAssets (410), current prices e.g. USDT 0.99919, USDC 0.99992
- keys: peggedAssets, chains
- No historical time series in this response; current snapshot only.

**Gates:**
- direct_usd_anchor: yes for current
- historical_depth_observed: no (current only)
- pit_times: no
- recommend: NONE (fails historical price gate)

**Note:** Supply family, not price history for PIT FX.

