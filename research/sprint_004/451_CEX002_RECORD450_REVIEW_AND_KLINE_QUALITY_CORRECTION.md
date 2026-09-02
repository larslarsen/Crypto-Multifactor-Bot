# CEX-002 Review 451 - Record 450 Review and Kline Quality Correction

- **Date:** 2026-09-02
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** accept the terminal run facts, correct the capacity units, adopt ADR-0035, and
  authorize one bounded Sol High source/test correction
- **Gate 2:** `ACCEPTED`
- **Gate 3:** `IN_PROGRESS`
- **Next required actor:** Sr Dev - Codex Sol, High
- **Next ticket:** `NONE`

## Plain-language decision

The download is not broken and will not be restarted. Record 450 reached one row Binance itself
published with impossible volume relationships. A complete new read-only scan found 67 such rows
out of 16,033,509, concentrated in five hours. The raw files are authentic, but authentic bad data
must not be passed to an experiment as if it were valid.

ADR-0035 keeps every row that is valid for the product being built. The price-bar product excludes
40 rows whose total volume is internally inconsistent. The trade-flow product excludes all 67
rows because it also requires the taker-buy fields. Each exclusion becomes an explicit one-hour
quality gap tied to the original raw row. No value is edited or guessed, no product schema changes,
and no data is downloaded.

## Record 450 disposition and capacity correction

Review 451 accepts these Record 450 terminal facts:

- the one authorized resume ran to an observed exit 1 after about 1,500 seconds;
- the exception was `KlineNormalizationError: taker-buy base volume exceeds total`;
- no process remained at observation;
- generation 0 was unchanged and nothing was downloaded;
- both hidden roots contained 20,335 matching Parquet/lineage pairs, empty staging, and no
  completion or gap artifacts; and
- the partial hidden artifacts remain unaccepted and untouched.

Record 450's two available-capacity values are not bytes. They are default `df` 1-KiB block
counts that were labeled incorrectly:

| observation | recorded count | correct unit | correct bytes |
|---|---:|---|---:|
| preproof | 41,509,740 | KiB | 42,505,973,760 |
| terminal | 37,658,760 | KiB | 38,562,570,240 |

Both corrected byte values exceed the 33,566,545,257-byte protected floor. Record 450 remains
preserved; this review is its forward correction. There is no capacity emergency and no output
cleanup is authorized.

## Complete read-only corpus proof

The reviewer rescanned every row from the same accepted generation-0 inputs used by the
normalizer:

- `data/cex002_qualify/gate2/state.sqlite`, opened query-only;
- `data/cex002_qualify/gate2/content`, read without mutation; and
- all 35,642 selected one-hour kline ZIPs, totaling 16,033,509 physical rows.

Every price and volume token was parsed as `Decimal` at precision 80. For each nonzero base-volume
pair the scan tested the exact mathematical requirement
`low * base_volume <= quote_volume <= high * base_volume`; zero base required zero quote. It
performed the same test for taker-buy volume and retained the existing taker-buy-within-total
checks. It then independently rebuilt per-symbol missing-hour topology for the raw, bar-valid, and
trade-flow-valid timelines.

The result is exact:

| fact | value |
|---|---:|
| physical rows | 16,033,509 |
| inconsistent total-volume pairs | 40 |
| inconsistent taker-buy pairs | 29 |
| rows in both pair sets | 2 |
| union of affected rows | 67 |
| taker-buy-within-total failures | 1 |
| affected symbols | 43 |
| affected symbol/month partitions | 57 |

The 67-row canonical evidence stream uses UTF-8 JSON Lines, one trailing LF per row, lexicographic
`(source_key, source_row_ordinal)` order, sorted keys, and compact separators. Each row contains
`source_key`, zero-based data-row ordinal, `open_time`, `high`, `low`, the four source volume
tokens, and exact booleans for total-pair inconsistency, taker-buy-pair inconsistency, and
taker-buy-within-total failure. Its identity is:

```text
bytes  = 25,439
sha256 = d5f2c236c851f03f0bc1da1b8fc8c84ba0024b154730f2425b2ca1db01f46bac
```

Affected UTC hours are:

| open time (ms) | UTC | rows |
|---:|---|---:|
| 1695139200000 | 2023-09-19T16:00:00Z | 17 |
| 1695214800000 | 2023-09-20T13:00:00Z | 15 |
| 1695279600000 | 2023-09-21T07:00:00Z | 12 |
| 1699959600000 | 2023-11-14T11:00:00Z | 7 |
| 1701345600000 | 2023-11-30T12:00:00Z | 16 |

Affected symbols are `AAVEUSDT`, `ALGOUSDT`, `ALICEUSDT`, `ANTUSDT`, `ARBUSDT`, `ARUSDT`,
`BALUSDT`, `BATUSDT`, `BLUEBIRDUSDT`, `BNXUSDT`, `COMBOUSDT`, `CRVUSDT`, `DARUSDT`,
`DOTUSDT`, `DYDXUSDT`, `ENSUSDT`, `FILUSDT`, `FLOWUSDT`, `FXSUSDT`, `GTCUSDT`, `HOOKUSDT`,
`INJUSDT`, `KAVAUSDT`, `KLAYUSDT`, `KSMUSDT`, `LITUSDT`, `LQTYUSDT`, `MAGICUSDT`,
`NEOUSDT`, `NMRUSDT`, `OMGUSDT`, `ONTUSDT`, `SNXUSDT`, `SUIUSDT`, `THETAUSDT`, `TRBUSDT`,
`UNFIUSDT`, `XRPBUSD`, `XRPUSDT`, `XTZUSDT`, `XVSUSDT`, `ZENUSDT`, and `ZRXUSDT`.

The rebuilt topology proves:

| timeline | rows | gap rows | unavailable hours |
|---|---:|---:|---:|
| authenticated raw | 16,033,509 | 114 | 8,003 |
| bar-valid | 16,033,469 | 154 | 8,043 |
| trade-flow-valid | 16,033,442 | 181 | 8,070 |

This supersedes Review 446's zero-corrupt-row statement and its row/gap equations. The reviewer
owns that earlier false conclusion: the first scan did not expose these required cross-field
economics, and it also failed to report the one already-required taker-buy-within-total violation.
No acquisition or developer action caused the bad source rows.

## First stopping row and alternate-package check

The stopping source is:

```text
source_key = data/futures/um/monthly/klines/UNFIUSDT/1h/UNFIUSDT-1h-2023-11.zip
source_sha256 = d180bf1e2f7fcb002c650bfaf4b88177425a6083a577d126eacef7ee69e2ae5d
source_row_ordinal = 708
open_time = 1701345600000
row = 1701345600000,11.724,11.737,11.593,11.633,41538,1701349199999,1430601.9399,11127,51617.3,601711.7884,0
```

The total quote/base ratio is approximately 34.44 despite the candle range 11.593-11.737, and
taker-buy base 51,617.3 exceeds total base 41,538. The taker-buy quote/base pair itself implies a
price inside the candle range, so inventing which total-volume field is wrong would be guesswork.

The reviewer fetched Binance's official daily checksum and ZIP for that same date into memory
only. The sidecar declared SHA-256
`18ae507ee2607bc7dc9d5e5b4147979bd6a199d82d9fca04995c01a0f4febe63`; the 1,327-byte ZIP
matched it exactly and contained the identical row. The daily package is therefore not a repair
source for the stopping defect. No file was added to or changed in the repository or accepted data
store by that diagnostic.

## Accepted architecture correction

ADR-0035 is adopted. It preserves the accepted product schemas and partitions while applying
product-specific row validity:

- bar rows require an internally valid total-volume pair;
- trade-flow rows require valid total and taker-buy pairs plus taker-buy within totals;
- excluded rows become one-hour `provider_invalid_required_fields` quality gaps with complete raw
  lineage and invariant flags; and
- completion descriptors record the exact product-specific exclusions and corrected equations.

The 20,335 existing hidden pairs are not deleted. Corrected execution may rehash/reuse unaffected
Parquets, publish corrected affected artifacts beside unreferenced old content addresses, and
complete only from the corrected descriptor's explicit ordered set.

## Sol High source authorization

Sr Dev - Codex Sol using GPT-5.6-sol High is authorized to edit exactly:

- `src/cryptofactors/ingest/binance_usdm_klines.py`; and
- `tests/ingest/test_binance_usdm_klines.py`.

The CLI remains byte-identical at SHA-256
`f1a4df5065de841f15d1bbbb1692b98bf97a010c37f7294f9230d0c02d240542`.

Sol implements ADR-0035 literally. The source must use exact arithmetic; distinguish raw,
bar-valid, and trade-flow-valid rows; keep the 27 bar-valid/taker-invalid rows; emit one typed gap
per product exclusion; bind exact source exclusion facts into quality-gap lineage; preserve
product-specific physical/excluded/product equations; advance corrected completion/lineage
versions; keep duplicate and every non-volume semantic failure fail-closed; and reuse unaffected
content-addressed outputs without deleting any old artifact.

Tests must prove both volume-pair boundaries, zero-pair handling, taker-within-total, bar-only
retention, product-specific exclusion, exact gap reasons/lineage/equations, interrupted resume with
old unreferenced content, and the exact corrected full-corpus constants. No product schema or
accepted sizing/acquisition authority may change.

Under the targeted senior exception, Sol may run exactly once:

```text
PYTHONPATH=src .venv/bin/python -m pytest tests/ingest/test_binance_usdm_klines.py -q --tb=short
```

Sol stops on the first nonzero result and reports the exact command/output, hashes, and line counts.
It performs no real-data run, data or output mutation, integration, repository-record edit, Git,
network, acquisition, cleanup, catalog transaction, NautilusTrader work, experiment, model,
Harmonic Trader repository work, PAPER, LIVE, other product, or next-ticket work. Hermes remains
unauthorized pending reviewer source inspection.

## Reviewer publication scope

Under the AGENTS.md reviewer governance-publication exception, the reviewer publishes exactly:

- `docs/adr/0035-product-scoped-provider-inconsistent-kline-exclusions.md`;
- `research/sprint_004/451_CEX002_RECORD450_REVIEW_AND_KLINE_QUALITY_CORRECTION.md`;
- `docs/handoff/CURRENT_TASK.md`; and
- `tickets/CEX-002.md`.

All source, test, CLI, data, hidden output, runner, and unrelated dirty paths remain unstaged and
untouched.
