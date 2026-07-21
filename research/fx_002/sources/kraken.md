# Kraken - USDTZUSD (source note)

**Provider role in repo:** Spot venue, DEFER for bulk per 02_DATA_SOURCE_PLAN.md and Sprint-003 decisions. REST known to cap at recent (720 entries for some).

**Tested endpoint:** /0/public/OHLC

**Exact calls and evidence:**

1. Old since test (to check historical backfill):
   - URL: https://api.kraken.com/0/public/OHLC?pair=USDTZUSD&interval=1440&since=1651363200
   - retrieval: 2026-07-21T07:22:40Z
   - sha256: fe545558a74fd1e240975ff014f324107d01faf844bf18879ab8bed6048deb46
   - size: 64759
   - external: /tmp/fx_002_raw/kraken/usdtzusd_old_since.json
   - returned: 721 rows, min_ts=1722384000 (2024-07-31), max_ts=1784592000 (2026-07-21)
   - Note: since=2022 ignored; only recent window returned. Confirms REST is current/incremental only. Matches known Kraken REST limit (not suitable for full historical PIT without bulk).

2. Recent sample:
   - URL: https://api.kraken.com/0/public/OHLC?pair=USDTZUSD&interval=1440
   - retrieval: 2026-07-21T07:15:26Z
   - sha256: 8dfd26f890d060f1a10c481e903d045c2e1424a255c948d5e5349ae54bb670b3
   - size: 2744
   - external: /tmp/fx_002_raw/kraken/usdtzusd_30d.json
   - returned recent rates ~0.998-1.00

**Timestamps:**
- OHLC array[0] = unix timestamp (close time for the bar).
- No separate publication time or availability time in response.
- Retrieval time recorded separately.
- For PIT: availability would be retrieval + any processing, but since capped, not historical.

**Revision behavior:**
- In captured samples, no evidence of revision (bars not changing on re-fetch in this test).
- But no vintage or checksum for historical REST; bulk may have.

**Bulk test:**
- Official: https://support.kraken.com/articles/360047124832-downloadable-historical-ohlcvt-open-high-low-close-volume-trades-data
- In this audit, the direct bulk host/path not directly curlable without following (quarterly CSVs require navigation).
- No direct access to full historical OHLCVT in bounded test; therefore historical PIT not confirmed from REST.
- Per repo: DEFER pending successful bulk acquisition.

**Depeg coverage:**
- No valid historical depeg sample from 2022 because of cap. The "depeg" data captured was recent (2024+).
- Cannot claim 2022 coverage from REST.

**Direction:**
- Pair USDTZUSD: price is ZUSD (USD) per 1 USDT.
- Matches "USD received per one unit of stablecoin".

**Licensing:**
- Public market data per Kraken docs. No terms captured in raw (no /terms page fetched in this test). Assume standard public.

**PIT gates status for Kraken:**
- Direct USD: yes
- Historical depth: no (REST capped; bulk unverified in audit)
- Observation/availability distinguished: no (only bar time + retrieval)
- Revisions: unknown (no evidence captured)
- Raw reproducible: partial (REST yes, but not historical)
- Licensing clear: partial (no explicit terms captured)
- Depeg historical: no

**Conclusion:** Does not pass all gates. Cannot recommend as primary without bulk audit.

