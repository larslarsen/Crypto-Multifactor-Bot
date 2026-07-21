# Binance

**Corrected archive evidence (with /data/ path):**
- USDTUSD 2022-05-01: 404 NoSuchKey (correct path). Proves absence for that depeg date.
- USDCUSD 2022-05-01: 404 NoSuchKey. Proves absence for that depeg date.
- USDTUSD 2026-07-20: 200, Last-Modified Tue 21 Jul 2026 02:43:50 GMT, 224 bytes. 1-row daily CSV (no header row): open_time=1784505600000000, close=0.99920. Schema confirms USD per USDT.
- USDCUSD 2026-07-20: 200, similar, close=0.99981, USD per USDC.
- CHECKSUM sidecars for 2026-07-20: 200, match local zip shas exactly. Integrity ok.

**Symbol info (live):**
- USDTUSD: base=USDT, quote=USD, TRADING. rate: USD per USDT
- USDCUSD: base=USDC, quote=USD, TRADING. rate: USD per USDC

**Docs:**
- No explicit fiat definition for USD quote found.

**Conclusions from corrected evidence:**
- Historical depth observed: recent/partial (2026-07-20 object succeeds; 2022-05 fails).
- Depeg sample: failed (404 on 2022-05-01 for both).
- Direct USD anchor: yes (quote=USD).
- PIT times: UNKNOWN (no publication/availability semantics in data).
- Revisions: UNKNOWN.
- Raw reproducible: yes (for successful objects and checksums).
- Licensing: UNKNOWN.
- Fiat semantics: UNKNOWN.
- Source status: REJECTED (failed depeg coverage + multiple UNKNOWNs).
- Recommendation: NONE
