# CEX-002 Spark Gate 1 Source Review

Date: 2026-08-18

Reviewer: Lead Quantitative Finance Researcher/Engineer

Decision: **REJECT SOURCE DROP; DO NOT INTEGRATE**

## Reviewed final source identities

Spark initially wrote the drop under the preserved CEX-001 names, then moved it to the
authorized non-colliding CEX-002 paths before declaring completion. This review applies
only to the final stable paths and hashes:

| Path | SHA-256 | Bytes |
|---|---|---:|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `54a41161d81dfea35a9219a8095d946bbe25d6e5f6aa1bd3255a5ef2735cfa41` | 42,829 |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `d17cd01023f2cddb07e5741d4de5193b2cffadfd6d3f61a3d4b595164098ba38` | 11,446 |
| `scripts/research/qualify_binance_usdm_harmonic_sources.py` | `61db02059bdd045d6da634ab48b247592dd87e5641132f2fb35550c46cd0df37` | 4,051 |
| `tests/acquisition/fixtures/binance_usdm_harmonic_qualification/.gitkeep` | retained empty-directory marker | 57 |

The prior rejected CEX-001 versions recorded in review 59 no longer exist at their
original working-tree paths. Their recorded hashes differ from the transient Spark
content. They are not silently declared preserved or restored; the owner must re-supply
that rejected source drop if exact source-byte preservation is required.

## Blocking findings

1. ZIP schema inference still treats every non-empty first CSV row as a header
   (`binance_usdm_harmonic_qualification.py:407-426`). A direct real-shaped headerless
   probe returned `('1', '7000.0', '0.5', '3500.0', '1577836800000', 'true')` as field
   names. The test helper creates only synthetic headed ZIPs, repeating the exact defect
   rejected in CEX-001.
2. Resume trusts a progress row and the existence of a content-addressed path without
   rehashing the file (`:785-807`). A direct probe replaced the accepted content with
   `tampered`; the second run returned `reused_existing=True` and the old reported hash
   while the actual SHA-256 differed.
3. The Coinalyze implementation does not call or parse Coinalyze. It fabricates URL
   receipts for nonexistent paths `/liquidation/daily`, `/open-interest/daily`,
   `/funding/daily`, and `/ohlcv/daily` (`:50-55,1049-1055`). The official API contract
   uses `/liquidation-history`, `/open-interest-history`, `/funding-rate-history`, and
   `/ohlcv-history` with `symbols`, `interval`, `from`, and `to`. No real response schema,
   non-empty sample, retention evidence, unit evidence, or Binance overlap reconciliation
   is implemented.
4. The CLI permits `--coinalyze-api-key` (`qualify_binance_usdm_harmonic_sources.py:48`),
   exposing a secret through shell history/process arguments contrary to the exact
   `COINALYZE_API_KEY`-only contract. The internal `CoinalyzeReceipt` also retains the raw
   credential-bearing URL before later report projection; the redaction test checks only
   the final projected report.
5. The S3 client parses `NextMarker` and V2 continuation tokens but always sends
   `continuation-token` without `list-type=2` (`binance_usdm_harmonic_qualification.py:625-633`).
   A V1 `NextMarker` page therefore cannot be continued correctly. Full inventory remains
   unproved.
6. `binance_usdm_bar_1m` descends and counts every discovered kline interval rather than
   explicitly selecting `1m`. The test positively accepts either `/1m/` or `/5m/`. Its
   reported object and byte totals therefore do not describe the named one-minute product.
7. The unproved 64 MiB object cap remains (`:825`), so large real monthly trade objects
   fail before their actual sizes are qualified. This repeats a CEX-001 rejection.
8. A missing provider checksum is accepted (`:808-815`), and any listed product with any
   retained sample can become `official_complete` despite missing declared families,
   listing/sample incidents, unknown sizes, incomplete symbol coverage, or absent
   checksums. The gate can silently promote partial source evidence.
9. Arbitrary `licensed_quotes` JSON still upgrades a product to `LICENSED`
   (`:1029-1033`), and the test requires this behavior. CEX-002 authorizes no paid source,
   and a label/quote is not source authority. This repeats a CEX-001 rejection.
10. Derived trade-flow, gap, and bundle products are always classified unsupported and
    then included in `blocked_products` (`:653-659,1070`). The source gate is therefore
    permanently blocked for outputs that are not source families, again repeating a
    CEX-001 rejection.
11. Coinalyze data never changes liquidation authority: the liquidation product has no
    archive family, its fabricated receipts do not affect its matrix row, and it remains
    inaccessible even with a key. The main purpose of the correction is not implemented.
12. Cost calibration inventories `bookTicker` only. It omits Binance's available
    `bookDepth` family while marking the cost product `official_complete=True` when any
    book-ticker object exists.
13. Delisted identification depends on an optional owner-supplied current-symbol JSON.
    The production CLI neither acquires nor authenticates the official current contract
    response, and the archive-name union does not prove historical `PERPETUAL` contract
    type/version semantics.
14. The CLI returns exit code zero for a `BLOCKED` matrix unless the operator remembers
    `--require-complete` (`qualify_binance_usdm_harmonic_sources.py:54,106-113`). That is
    silent operational partial success under the default command.
15. Report output is called deterministic, but no test proves byte identity across an
    interrupted/resumed equivalent run. Generated/retrieval timestamps and mutable local
    paths are included without a defined identity projection.

## Static and direct evidence

- In-memory Python compilation of the final three source/test paths: PASS.
- Targeted Ruff on the final three paths: PASS.
- Direct headerless-ZIP probe: FAIL; numeric data row accepted as schema fields.
- Direct content-addressed-resume tamper probe: FAIL; tampered bytes reused without hash
  verification.
- Pytest, network qualification, catalog mutation, data acquisition, and integration were
  not run because source inspection rejected the drop.

## Routing decision

This is no longer bounded mechanical plumbing. Correctness depends on source authority,
credential containment, pagination semantics, immutable replay, and truthful economic
coverage. The correction is assigned to Sr Dev — Grok Build using Grok 4.6 High. Higher
reasoning effort is not authorized unless this bounded correction fails review.

No Spark correction, Jr integration, test execution, network call, catalog mutation, or
data publication is authorized against the rejected hashes.
