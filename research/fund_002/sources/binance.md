# FUND-002 — Source Note: Binance USD-M Funding Archive Family

**Environment:** 2026-07-21 capture from `data.binance.vision` and `fapi.binance.com`.
**Status:** Evidence captured; provider documentation for funding family is partial.

## Official Documentation Sources

- Official Binance Public Data README: `https://raw.githubusercontent.com/binance/binance-public-data/master/README.md`
  - Final captured ETag: `d6bc0ba6325b02747dd669b4f1d39811afd068fa3f81b7b17b920f72b69e1752`
  - Final captured body sha256: `085ab91377aa9325d44f4c7ad27cce4ab381e158403e1d7df2bad39d1a66f7c6`
  - Documents aggTrades, klines, trades for USD-M and COIN-M futures.
  - States: each ZIP has a `.CHECKSUM`, archived files may be updated, and the repository declares
    `Licence: MIT`.
  - Does not document funding archive schema, interval semantics, rate unit/sign/formula, replacement
    policy applicability, or redistribution scope for metadata/hashes.

- `data.binance.vision` homepage confirms monthly listing pages exist.
  - Listing bodies in this environment return JS-dependent/minimal content; cannot enumerate replacement
    register from listing alone.

- Official derivatives/spec pages (`developers.binance.com/docs/...`, `binance-docs.github.io/...`) returned
  empty or near-empty bodies in this environment.

## External Documentation Capture Paths

All exact captures live outside Git under `/tmp/fund_002_raw/docs/`:
- README body: `docs/binance_public_data_readme_latest.md`
- README response headers: `docs/binance_public_data.headers`
- Funding archive responses: `docs/BTCUSDT_2025_01.headers`, `docs/BTCUSDT_2025_01.zip.CHECKSUM`, etc.
- REST response body: `docs/rest_funding_body.json`
- REST response headers: `docs/rest_funding_headers.txt`

## Git Notice

This `sources/binance.md` is metadata only. Raw ZIP files and exact headers/bodies remain outside Git under
`/tmp/fund_002_raw` and are represented by hashes and metadata only.

## Observed Schema

Monthly funding ZIP member: `calc_time,funding_interval_hours,last_funding_rate`
- `calc_time`: 13-digit integer UTC epoch milliseconds in all sampled rows and in REST `fundingTime`.
- `funding_interval_hours`: integer, value `8` in all sampled rows.
- `last_funding_rate`: numeric decimal, all sampled values are positive.

## Replacement Evidence

Provider `.CHECKSUM` sidecars match all three sampled ZIP byte-for-byte. This proves download integrity.
Funding-specific replacement register and correction policy are not demonstrated in captured evidence.
The README's generic "archived files may be updated" statement does not establish funding-specific applicability
or timing.

## Licensing

Captured README text states `Licence: MIT` for the repository.
Exact redistribution terms for funding archive family metadata/hashes are not further established by this capture.
