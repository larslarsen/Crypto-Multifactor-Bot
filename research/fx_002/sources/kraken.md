# Kraken USDTZUSD

**Capture from register:**
- evidence_id: KRAKEN-USDTZUSD-OLD-SINCE
- request_url: https://api.kraken.com/0/public/OHLC?pair=USDTZUSD&interval=1440&since=1651363200
- retrieval_utc: 2026-07-21T07:22:40Z
- http_status: 200
- sha256: 1eed62a8423a4d6cb71f901085de3381c9c219546c99dde248b28c42048ece95
- byte_size: 64759
- external_path: /tmp/fx_002_raw/kraken/usdtzusd_old_since.json
- returned_bounds: min_ts=1722384000 (2024-07-31), max_ts=1784592000 (2026-07-21), rows=721
- rate_direction: USD per USDT
- licensing_url: https://www.kraken.com/legal
- licensing_status: UNKNOWN: no terms evidence captured
- notes: Old since ignored; only recent cap returned. Confirms non-historical for backfill per Sprint-003.

**Timestamp semantics:**
The response timestamp is the OHLC interval timestamp. Not publication or availability time without further official documentation.

**Conclusion for this candidate:**
Historical depth: no (capped to recent window).
Direct USD anchor: yes.
PIT times: no.
Revisions: UNKNOWN.
Depeg sample: no (no historical).
Raw reproducible: yes.
Licensing clear: no.
Source status: REJECTED (fails historical depth and PIT times gates).
