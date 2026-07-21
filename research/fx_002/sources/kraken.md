# Kraken - USDTZUSD (source note - corrected)

**Endpoint tested:** https://api.kraken.com/0/public/OHLC

**Exact old-since capture (to prove cap):**
- request: pair=USDTZUSD&interval=1440&since=1651363200
- retrieval_utc: 2026-07-21T07:22:40Z
- sha256: fe545558a74fd1e240975ff014f324107d01faf844bf18879ab8bed6048deb46
- byte_size: 64759
- external: /tmp/fx_002_raw/kraken/usdtzusd_old_since.json
- returned: rows=721, min=1722384000 (2024-07-31), max=1784592000 (2026-07-21)
- Proof: old 2022 since ignored; only recent window. Per Sprint-003, Kraken REST is not for historical backfill.

**Timestamp semantics:**
- The timestamp in OHLC is the bar's interval time (start or close per Kraken docs). Not labeled as publication or availability without further docs.
- No separate provider publication time in the response.
- Retrieval time recorded.

**Historical depth:** REST does not provide full history; capped to recent. Bulk downloadable per support article not fully audited in this bounded test for FX (no direct stable USD in plan for Kraken FX).

**Depeg:** No 2022 sample because of cap. Recent shows ~0.998 levels.

**Rate direction:** Price in response is USD per USDT (ZUSD per USDT).

**Licensing:** Public API, terms at kraken.com/legal (not captured in this audit, so UNKNOWN for gate).

**Gates status:**
- direct_usd_anchor: yes
- historical_depth_observed: no (capped)
- pit_times_distinguished: no (bar time only)
- revisions_observed: UNKNOWN
- depeg_sample: no (no historical)
- raw_reproducible: yes (for captured window)
- licensing_clear: UNKNOWN (no citation)
- recommend: NONE

**Bulk note:** Official bulk is quarterly OHLCVT downloads. Not tested for this FX candidate in this audit.

