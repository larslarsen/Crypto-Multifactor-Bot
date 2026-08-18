# CEX-002 Grok Gate 1 Corrective Source Review

Date: 2026-08-18

Reviewer: Lead Quantitative Finance Researcher/Engineer

Decision: **REJECT RESIDUAL SOURCE DEFECTS; DO NOT INTEGRATE**

## Reviewed source identities

Committed control-plane base:
`HEAD == origin/main == 848ed2a7049b6a696d7f06502698638f58279df9`.

| Path | SHA-256 | Bytes |
|---|---|---:|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `24907fd96148f80ff13827e7b11fef5196a0e62fe8bfd07d6282ed05bbbd832d` | 65,531 |
| `scripts/research/qualify_binance_usdm_harmonic_sources.py` | `af3aca3cf461ce2cfd31dd8db5b4aa53a9c1e5332a7bc8a622f250a3bb2855f6` | 3,127 |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `0587a59e32290e1516532ec1413d3566fd51836d2bfb47c2dd5712747c16bfcf` | 19,913 |
| `tests/acquisition/fixtures/binance_usdm_harmonic_qualification/.gitkeep` | `8267c14d4f23f9e73644a385361b2cd9c7addcf12565b80308f22c967e58b342` | 57 |
| `tests/acquisition/fixtures/binance_usdm_harmonic_qualification/coinalyze_funding_rate_history.json` | `01639c0636c23ba4c009627f227f28930b063f61988b6bff49bc13334122ce9f` | 225 |
| `tests/acquisition/fixtures/binance_usdm_harmonic_qualification/coinalyze_future_markets.json` | `cfe4bfc7a5c85e9ec6c550859438d431353109a0a58b30ebd7aeab84d6ac37a9` | 741 |
| `tests/acquisition/fixtures/binance_usdm_harmonic_qualification/coinalyze_liquidation_history.json` | `5f5d16ffaaff9015bacd0b6402954ddc1616ad5efcfdd23288ef1c50739de38d` | 159 |
| `tests/acquisition/fixtures/binance_usdm_harmonic_qualification/coinalyze_ohlcv_history.json` | `be4a3891542e08b25356bdabbf347e2916ad2272b1325e7397ca95005d81ad0f` | 465 |
| `tests/acquisition/fixtures/binance_usdm_harmonic_qualification/coinalyze_open_interest_history.json` | `3e9525335426ce0c95f3a35b40ea1f626e1ab388941ef77ae5f66d29f062f141` | 211 |
| `tests/acquisition/fixtures/binance_usdm_harmonic_qualification/exchange_info.json` | `0e013714dd49fae5591228eb069bab6bcdef9049a755eef88a65adba709c2e2f` | 709 |
| `tests/acquisition/fixtures/binance_usdm_harmonic_qualification/headed_funding.csv` | `3d28d1874797a6ff8cb572d379384c5c32b0f1d755f1dd084776c639ea743500` | 99 |
| `tests/acquisition/fixtures/binance_usdm_harmonic_qualification/headerless_book_depth.csv` | `91bd3ae8957a8ef3afa08d04adfb7c70dc40d6b22717c5a5f857f3e0262b2f8d` | 30 |
| `tests/acquisition/fixtures/binance_usdm_harmonic_qualification/headerless_book_ticker.csv` | `4f24742e4968b19fd19fe6d4ff0c68b9cd01992f62a81ee23cb411fa600ee9ec` | 52 |
| `tests/acquisition/fixtures/binance_usdm_harmonic_qualification/headerless_klines.csv` | `941d441a11516391b7a3f70e983ce9a845e2a61eabea3708aa0b0a4856368afc` | 170 |
| `tests/acquisition/fixtures/binance_usdm_harmonic_qualification/headerless_metrics.csv` | `037032b2d5f65296e7934f9f3964eb32021aaf8e134b137015eeecdc42f81d2a` | 54 |
| `tests/acquisition/fixtures/binance_usdm_harmonic_qualification/headerless_trades.csv` | `b7960abfb45e9e967c5d9f289830c5bc64dcf2b971fe91ed585b8b7c8bf10a8a` | 81 |

## What the rewrite fixed

The reviewed source closes most review-61 findings: ListObjectsV2 pagination, exact `1m`
descent, required provider checksums, rehash-on-resume, removal of the fixed 64 MiB sample
cap, environment-only Coinalyze key input, real history endpoint names, authenticated
current contracts, derived-product source-gate treatment, book-depth plus book-ticker
inventory, deterministic identity projection, and nonzero blocked exit behavior.

Those accepted corrections must not be rewritten in the next drop.

## Residual blocking findings

1. **Known headerless metrics data is still accepted as a header.** Schema inference calls
   a row headerless only when every token is numeric or boolean. The supplied real-shaped
   metrics fixture contains the native string symbol, so the first data row is returned as
   field names. Direct output was
   `SchemaIdentity(kind='headed', fields=('1577836800000', 'BTCUSDT', ...),
   family_hint='metrics')`. More generally, any nonnumeric unexpected first row is accepted
   as a headed schema instead of being checked against the known family header. This leaves
   review-61 finding 1 open for at least the metrics family.
2. **Aggregate family counts still silently promote incomplete symbol coverage.** Matrix
   completeness checks only total objects, aggregate family presence, sample checksums, and
   incidents. It neither records nor compares per-family/per-symbol object coverage against
   the discovered universe. A direct two-symbol probe left both trade and aggregate-trade
   prefixes empty for `ETHUSDT`; the report nevertheless returned
   `binance_usdm_trade authority='official', official_complete=True`, reported two
   discovered product symbols, and omitted the product from `blocked_products`. This is the
   silent partial-source promotion prohibited by review-61 finding 8 and CEX-002.
3. **Coinalyze qualification does not authenticate the requested/returned symbols or the
   reported unit.** Requesting only `ETHUSDT_PERP.A` while all four history fixtures return
   `BTCUSDT_PERP.A` still qualifies liquidation authority. The future-markets response is
   checked only for any Binance perpetual, not the requested markets; history products are
   not required to return the requested set consistently. The report also emits the literal
   string `future-markets.oi_lq_vol_denominated_in` rather than the matched market's actual
   value (`BASE_ASSET` in the fixture). Thus the source identity and unit evidence required
   by review-61 findings 3 and 11 remain unproved.

The bounded correction must add focused tests which fail on exactly these three probes.
It must also retain redacted content hashes and retrieval identities for the bounded real
Coinalyze responses so the later real Gate 1 report has source provenance rather than only
derived counts and first/last timestamps.

## Role-boundary incident

Grok was explicitly prohibited from test execution. The target pytest bytecode was created
after the final source/test-source writes, independently corroborating the owner's report
that Grok ran tests. Those results are unauthorized and are not acceptance or integration
evidence. This process violation does not change the reviewed source hashes, but Jr Dev —
Hermes must still execute every authorized command after source acceptance.

## Reviewer evidence

- In-memory compilation of the three Python paths: PASS.
- Focused Ruff check of the three Python paths: PASS.
- Scoped `git diff --check`: PASS.
- Direct headerless-metrics probe: FAIL as described above.
- Direct per-symbol coverage probe: FAIL as described above.
- Direct Coinalyze requested/returned-symbol probe: FAIL as described above.
- Pytest and network qualification: not run by the reviewer because source is rejected.

## Routing and bounded correction

This remains source-authority logic, so the minimum-capable formal role is Sr Dev — Grok
Build on Grok 4.6 High. No higher reasoning tier is authorized. The next drop is a surgical
patch to the reviewed paths only; it must preserve accepted logic and must not rewrite the
module.

Grok may change only the three reviewed Python paths and the existing bounded fixture
directory. It authors source and test source only. It performs no test or acceptance-command
execution, network run, integration, repository-record edit, Git operation, commit, push,
purchase, catalog mutation, or publication. It stops for reviewer source inspection with
exact hashes for every changed path. Jr integration remains unauthorized.
