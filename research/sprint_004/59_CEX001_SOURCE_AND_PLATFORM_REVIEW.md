# CEX-001 First Source and Platform Review

Date: 2026-08-18

Reviewer: Lead Quantitative Finance Researcher/Engineer

Decision: **REJECT SOURCE DROP; BLOCK BEFORE JR INTEGRATION**

> **Superseding decision:** The source-rejection findings below remain valid. The later
> platform recommendation and reduced proof-of-life choice are withdrawn by
> `research/sprint_004/60_CEX_DATA_DESTINATION_DECISION.md` and ADR-0017. CEX-002 now owns
> the full free Harmonic-ready data acquisition.

## Scope and boundaries

This is a source-only review of the first CEX-001 Gate 0/Gate 1 drop after the control-plane
pivot committed at `87ff3b3`. No test suite, network acquisition, catalog mutation,
purchase, data publication, or DEX work was authorized or performed. The existing DEX and
unrelated working-tree paths are preserved outside this review.

## Reviewed source identities

| Path | SHA-256 |
|---|---|
| `scripts/research/backfill_bitmex_funding.py` | `8f6f4dde96fb23c20e57da57373528cff6fc99d4e86d8db23fc0a12838f2b4e4` |
| `scripts/research/qualify_binance_usdm_sources.py` | `368bba1458a87694dced62db300c7115f494c34aea43c9259268814a3b175d1f` |
| `scripts/research/quarantine_bitmex_funding.py` | `61d0b52b74fc3b009c9223fdbec679d5f2054d042b5d4907e7d0bd75b902ed10` |
| `src/cryptofactors/acquisition/binance_usdm_source_qualification.py` | `fe68bbaa0740554c1f953c75afcd442b1ab82d69ad122c29883c807bd6bef1ce` |
| `src/cryptofactors/acquisition/bitmex_funding_quarantine.py` | `95f5529442143634261e58b53eec79b5a84f8e45990374d5f5056578b5c0e401` |
| `src/cryptofactors/catalog/dataset/__init__.py` | `1385930627cca8b3a45076f587c97eedd9e0be91b2de94570fbe87c9ec35292a` |
| `src/cryptofactors/catalog/dataset/catalog_store.py` | `b5f9014aed8484845b8c58cca14d33359db5250a5912144872b60098e50e2b34` |
| `src/cryptofactors/catalog/dataset/errors.py` | `0c90bc572b9b5b1a7f3103d07bc106764500aff40f62019ac1c10e60bc58693a` |
| `src/cryptofactors/ingest/__init__.py` | `369be49f416a5dabd0b661511cdd3077bcef12c3a0c8e9481778e09963bc8499` |
| `src/cryptofactors/ingest/bitmex_funding.py` | `f640de0bf909e45049d196a1dbfa3811f08d4d5a23e2455c7c93063a869cd454` |
| `tests/acquisition/test_binance_usdm_source_qualification.py` | `68f7e6f1d257759e883fe6d94a13448735fd20c0d9828ecc4015ccdddcf20bb9` |
| `tests/acquisition/test_bitmex_funding_quarantine.py` | `8b6e5f552a3d6112c17b227065639dad095c6142b534af11d0b1c3aeece39b29` |
| `tests/catalog/test_resolve_latest_by_type.py` | `b4056ab6abde09c0d7a07c58a33f2aa3b4dc80cea5046796d5c8bd1afb9beea6` |
| `tests/ingest/test_bitmex_funding.py` | `225feda553230319fca7fa781239a105b88823683d7cf32faf5e77fa45761306` |
| `tests/ingest/fixtures/bitmex_funding_source_shapes.json` | `974eec9aaf076ffff115fd929132352d18a8e54a400c2d0639d5073e9cb0c1e9` |

## Blocking source findings

1. `run_source_qualification` lists objects and sums bytes only for
   `sample_symbols` (`binance_usdm_source_qualification.py:746,773-797`) but reports those
   values as estimates for the full discovered family (`:843-885`). This materially
   understates object count and storage.
2. Kline archives are interval-partitioned below each symbol, but the runner lists only
   the symbol root (`:758-779`). It never descends the required `1m` prefix for trade,
   mark-price, index-price, or premium-index klines.
3. ZIP/CSV schema inference treats the first line as a header (`:338-350`). Binance
   futures archives can be headerless; the existing tests exercise synthetic headed ZIPs,
   so numerical data can be reported as a schema.
4. Historical membership is derived only from `monthly/trades` prefixes (`:396-406`). It
   neither unions daily/monthly history nor establishes contract type and effective
   versions, so it cannot prove every historically listed perpetual.
5. The list parser detects `IsTruncated` (`:274-301`) but the production path has no
   continuation-token pagination. Complete inventory is impossible beyond one page.
6. Real monthly downloads are hard-limited to 64 MiB (`:646-653`) without proving that
   selected objects fit. Early/middle/recent alphabetical objects are also not evidence of
   multiple liquidity regimes.
7. A JSON product label alone upgrades authority to `LICENSED` (`:839-842`) without
   validating vendor identity, schema, coverage, rights, sample, or quote. Derived gap and
   bundle outputs are simultaneously treated as unavailable source products, making the
   source gate permanently blocked for the wrong reason.
8. Quarantine preconditions return success immediately for an existing marker
   (`bitmex_funding_quarantine.py:326-336`), before checking exact catalog/file facts.
   Replay compares files only with the same invocation's pre-state (`:461-470`), so
   post-quarantine tampering can become the accepted baseline.
9. Missing or unreadable manifests are explicitly tolerated (`:292-302`), yet the emitted
   summary claims `preserved_manifest=true`. No expected manifest hash is a target
   precondition.
10. File and row inspection occurs before the transaction (`:512-529`); the transaction
    re-fetches only the row and performs an unconditional ID-keyed update (`:535-555`). It
    does not re-authenticate or compare-and-swap the reviewed row, so concurrent mutation
    can be overwritten.
11. Default catalog resolution filters quality but not publication state
    (`catalog_store.py:110-127`). A `PASS/SUPERSEDED` row remains consumable, contrary to
    the Gate 0 authority boundary.
12. The BitMEX fixture is not bound to retained raw response bytes, an endpoint receipt,
    or immutable raw-object identity. Its claimed real-response provenance is therefore
    not auditable.

## Static evidence

- Python compilation of the 15 reviewed source/test paths: exit 0.
- Targeted Ruff: exit 1 with four findings in
  `tests/catalog/test_resolve_latest_by_type.py` (two unused imports and two unused local
  assignments).
- `git diff --check`: exit 0 before this review record.
- `python3 scripts/check_repo_control.py`: exit 0 before this review record.
- Pytest was intentionally not run because source inspection rejected the drop before Jr
  integration authorization.

## Current data economics

“Paid CEX” and “paid DEX” refer to different products:

- Binance's public archive is free and checksummed for several trade/bar families, but it
  does not by itself supply the complete historical microstructure contract in CEX-001.
- Tardis currently lists Perpetuals at **$350/month Academic, $700/month Solo,
  $1,000/month Professional, and $3,000/month Business**. Solo/Academic provide CSV only;
  Professional adds replay and metadata APIs. Annual Academic/Solo/Professional access is
  four years; Business annual is the tier with all available history. Thus the likely
  Nautilus-integrated CEX choice is $12,000/year Professional and still does not cover the
  complete 2019-present history without combining sources; Business is $36,000/year.
  Source: [Tardis pricing](https://tardis.dev/) and
  [billing scope](https://docs.tardis.dev/faq/billing-and-subscriptions).
- CoinGecko Analyst is **$129 month-to-month** or **$103.20/month billed annually**. Its
  pool OHLCV can reach back to September 2021 only when GeckoTerminal began tracking the
  pool, skips no-trade intervals by default, limits a response to 1,000 bars and a request
  to six months, and exposes only recent pool trades. It is useful for a tracked-pool
  geometric OHLCV project, but it is not a purchase of DEX-003's factory-complete raw
  Swap/Sync history or survivorship authority. Sources:
  [CoinGecko pricing](https://www.coingecko.com/en/api/pricing) and
  [pool OHLCV contract](https://docs.coingecko.com/reference/pool-ohlcv-contract-address).
- Ethereum raw logs do not require a proprietary data license. Google Blockchain
  Analytics exposes Ethereum mainnet logs in partitioned BigQuery tables. Public-dataset
  storage is provider-paid; the first 1 TiB of query processing per month is free and
  subsequent on-demand analysis starts at $6.25/TiB. Exact extraction cost must be measured
  with a dry-run bytes estimate and cap; it must not be guessed. Sources:
  [Ethereum schema](https://docs.cloud.google.com/blockchain-analytics/docs/schema),
  [public datasets](https://docs.cloud.google.com/bigquery/public-data), and
  [pricing](https://cloud.google.com/bigquery/pricing).

## Platform recommendation

Do not continue building a proprietary catalog, backtester, paper/live engine, and both
market-data spines before proving the geometric-pattern research idea. Preserve this repo
as an evidence archive and move the active experiment to a small new project using
NautilusTrader as the event-driven catalog/backtest/paper/live substrate.

NautilusTrader is LGPL-3.0, Rust-native with a Python control plane, and uses the same
event-driven semantics across research and live execution. Its Parquet catalog supports
trades, quotes, order-book data, bars, mark prices, and registered custom data. Its Tardis
integration can stream normalized historical data directly into catalog-compatible daily
Parquet and permits free first-day-of-month samples without an API key. Sources:
[project and license](https://github.com/nautechsystems/nautilus_trader),
[data catalog](https://nautilustrader.io/docs/latest/concepts/data/), and
[Tardis integration](https://nautilustrader.io/docs/latest/integrations/tardis/).

This replaces our duplicated engine/catalog/harness work; it does **not** replace data
procurement, point-in-time feature discipline, labels, purged validation, or the geometric
ML research itself. The recommended first deliverable is a bounded proof-of-life on free
Tardis sample days plus free Binance archives: ingest real trade/quote/depth data, compute
one causal geometric candidate feature, run one deterministic backtest, and prove one
paper/sandbox path. Purchase decisions follow only after that vertical slice runs.

The three `Harmonic_Trader/docs/upstream/` proposals were read in full. Their durable
requirements remain valid under migration: pinned immutable data identities, a narrow
consumer boundary, event/availability/decision/execution clocks, separate aligned
price/OI/funding/liquidation/basis/cost products, typed gaps, and reconciled P&L. What
changes is ownership: Nautilus supplies the catalog, replay, simulation, and live substrate;
the new project supplies only vendor conversion/custom data, causal geometry/ML, validation,
and experiment manifests. The old proposal to first build and release our own wheel,
descriptor, allocator, and simulator should not be carried into the migration by default.

## Control decision

CEX-001 is `BLOCKED`. No source correction or Jr integration is authorized. The owner must
choose whether the reviewer should (a) supersede CEX-001 through a migration ADR and issue
one small Nautilus proof-of-life ticket, or (b) retain CEX-001 and authorize a data budget
before a fresh high-risk correction. Codex Spark is now the preferred low/medium-risk
boilerplate author; the rejected historical-authority and atomicity correction is reserved
for the senior role if CEX-001 resumes.
