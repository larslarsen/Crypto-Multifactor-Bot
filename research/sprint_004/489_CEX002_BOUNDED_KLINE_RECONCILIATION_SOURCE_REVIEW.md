# CEX-002 Review 489 — Bounded one-minute/hourly reconciliation source

Reviewer: Lead Quantitative Finance Researcher/Engineer
Ticket: CEX-002 (IN_PROGRESS)
Source actor: Sr Dev — Grok Build (grok-4.7 High)
Next ticket: NONE

## Decision and routing

The owner reports that Grok has almost all of its usage remaining and that access ends
tomorrow night. Prioritize substantive Grok implementation under the existing CEX-002
completion order. Grok completed the strict BitMEX correction; its six approved paths
are integrated and pushed at f85177d9f1d21fe1fd054d40035afbf62b4e457f. The reviewer
independently matched committed blobs, staged blobs and worktree hashes. Hermes passed
52 targeted cases, Ruff, repository control and source/staged whitespace checks.
Technical source integration is accepted. Record 488 publication and final Gate-0
disposition were still in progress when this disjoint source assignment began. Hermes
has now published Record 488 at 68e93069acfdaa0a2fc9d7d606f75feaa4fcd49f, and Review 487
accepts Gate 0. Its extra malformed Git-object probe and post-failure inspection remain
disclosed. No source repair or accepted-product rerun is warranted by those record errors.

Authorize Grok now for the independent source-only assignment below within the SAME
active ticket. This does not wait for administrative Record 488 publication. There is
one senior source actor; Hermes performs only the previously assigned record publication.
The reviewer reconciles the current-task header after Hermes returns it. Neither
actor may stage the other's paths. This assignment implements the missing bounded
one-minute/hourly comparison in Gate 4 and Review 474; it does not accept Gate 4 or the
bundle, and does not introduce a new product, acquisition generation or architecture.

## Five writable paths

- `src/cryptofactors/acquisition/binance_usdm_kline_comparison_sample.py`
- `src/cryptofactors/ingest/binance_usdm_kline_reconciliation.py`
- `scripts/research/reconcile_binance_usdm_klines.py`
- `tests/acquisition/test_binance_usdm_kline_comparison_sample.py`
- `tests/ingest/test_binance_usdm_kline_reconciliation.py`

Existing source, exports, schemas, dependencies, catalogs, data and records are read-only.
No installations, real downloads, real comparison runs, Git, commits, pushes, cleanup,
archive access or developer evidence publication. Use normal CLI approvals. Author all
test fixtures inside test source and temporary directories. No other senior is assigned.

## Fixed authorities and sample selection

Read the existing contracts in CEX-002 Gates 4-5, Review 474, ADR-0024/0025/0035, and the
accepted hourly schemas/normalizer. Do not reread historical ticket narratives. Relevant
references are `binance_usdm_klines.py`, the sizing module's final product schemas,
and the descriptor/authentication patterns in `reconcile_binance_usdm_coverage.py`.

Pin qualification report `research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json`
at SHA-256 `f27b2ba7e6eff3a8b1385d985c49ee64ef60a394737b1246130d0f37b9015f09`.
Select its **daily/klines, 1h** sample records only. These are ten role bindings and nine
distinct symbol/days; preserve the duplicate recent/delisted role without downloading twice:

| Symbol | Early | Middle | Recent | Delisted role |
|---|---|---|---|---|
| 0GUSDT | 2025-09-17 | 2026-03-21 | 2026-05-30 | none |
| 1000BTTCUSDT | 2022-01-26 | 2022-03-12 | 2022-04-11 | 2022-04-11 |
| KAIAUSDT | 2024-12-04 | 2025-10-25 | 2026-07-19 | none |

The expected comparison ZIP for each row is exactly
`data/futures/um/daily/klines/{symbol}/1m/{symbol}-1m-{date}.zip`, and its official
`.CHECKSUM` sibling, under `https://data.binance.vision/`. No listing, arbitrary URL,
alternative symbol/day, full one-minute history, or substitution is permitted. These
comparison inputs do not amend generation 0 or replace selected hourly raw sources.

Pin accepted hourly completions (read only):

- bar root `data/.cex002_bar_1h`, completion
  `3b803d3e84e5d0bf87064626cc0504e9ff92e225a53ba83cdd4e09c38a2e9fd7`;
- flow root `data/.cex002_trade_flow_1h`, completion
  `a165f9e57065514cadc95620c280a82dbad5032d17c19e1caf012c9d12a84d0a`.

Authenticate the completion and only its selected symbol/month descriptors, Parquet
hashes/schemas/row counts and lineage; do not rerun full-product audits or normalize any
accepted product. Bound row memory to one selected day plus one selected monthly
partition. Production CLI cannot override identity hashes, symbols, dates or schemas;
private test fixtures may inject a small policy without becoming a production bypass.

## Acquisition boundary

The acquisition module alone owns HTTP. Implement a callable bounded sample fetcher;
the reconciliation module stays offline. The CLI must require explicit `--fetch` for
network activity, and otherwise authenticate and reuse already retained sample evidence.
Grok must not invoke `--fetch` or any real run. A later Hermes assignment will name the
actual evidence root and execution command after source review.

Use existing dependencies and publication patterns. Enforce nine ZIPs maximum, 8 MiB
compressed per ZIP, 16 KiB per sidecar, 128 MiB decompressed per ZIP, one expected CSV
member, and at most 1,440 data rows/day. Enforce limits while streaming, regardless of
Content-Length. Bound request timeouts; no implicit unbounded retry or alternate source.
Reject redirects outside the exact official object, non-success HTTP, malformed/mismatched
checksum statements and filename, truncated ZIP, unsafe members, CRC failure, and path
escape/symlink destinations. Do not extract archive members onto the filesystem.

Retain exact ZIP and sidecar bytes with their hashes, source keys/URLs, byte sizes,
retrieval times, and source availability explicitly unknown. Use a caller-selected
isolated evidence root with immutable content-addressed files, same-directory temporary
publication, fsync/no-clobber, and a last-written complete sample manifest. Reuse only
after reauthentication; partial interrupted work must not appear complete. Conflicting
retained evidence fails; do not overwrite or repair it silently. Keep protected report,
accepted product and generation-0 roots read-only; reject overlapping evidence outputs.

## Independent economic comparison

Parse headed/headerless twelve-field Binance kline rows strictly. Require exact integer
millisecond times/counts, UTC day ownership, 60,000-ms opens and close=open+59,999;
finite exact decimal tokens representable by the accepted scale-18 contract, correct
OHLC ordering, nonnegative volumes/counts and taker values within totals. Do not call the
hourly normalizer to produce expected results. Aggregate with exact scaled integers so
ambient Decimal precision and binary floats cannot alter sums or comparisons.

Sort by native timestamp, collapse only identical duplicates with explicit counts, and
reject conflicting keys. Only a complete hour of 60 distinct native minute slots may
produce a comparable hourly observation. Missing/partial hours remain explicit gaps;
never fill a slot, stretch a period or infer a zero. Every parsed row must reconcile to
a compared hour, an identical duplicate or an explicitly uncomparable hour.

For a complete hour, independently compute first open, maximum high, minimum low,
last close, sums of base/quote volumes, integer trade counts, and taker-buy base/quote
volumes. Compare each applicable field exactly with the accepted bar and flow rows.
Recompute flow's sell volumes as total minus buy, and its imbalance fields according
to the frozen schema's existing equations (inspect the implementation to identify the
published quantity, do not assume a normalized ratio). Preserve signed/zero derived
values; a zero is valid only when supported by observed source rows. Compare by
symbol and exact open/close times, not row positions.

Honor ADR-0035's product-specific quality exclusions: a missing accepted row must be
explained by its authenticated quality-gap evidence, never synthesized from minutes.
Do not extend those exclusions to hide a new minute-source defect or a cross-interval
mismatch. Record the exact source tokens/ordinals and compared product values for each
discrepancy. A discrepancy returns nonzero and a durable FAILED evidence report; it
does not modify accepted data or automatically revoke earlier product acceptance.

An authenticated day with no comparable hour, an unexplained absent hourly row, missing
sample/role, failed input proof, or any unequal comparable field cannot yield PASS.
Require at least one successfully compared hour in every distinct sample day and every
early/middle/recent/delisted role. Partial boundary hours may be honestly reported as
uncomparable alongside successful full hours; do not relabel bounded sample success as
full-history reconciliation. Keep per-day/hour/field counts and explicit denominators.

Publish a deterministic, content-addressed comparison report plus a small completion
reference only after validation. Bind report/sample/product/source/code/config identities,
exact comparisons, gaps, mismatch counts and arithmetic policy. Real retrieval timestamps
remain in retained sample receipts; replay over identical retained inputs reuses byte-
identical evidence. No catalog transaction, bundle publication or invented source clock.
Failure must return nonzero without a successful completion marker. Read-only replay
must authenticate prior evidence rather than trust an existing PASS label.

## Tests and one targeted execution

Author meaningful temporary-fixture tests for sample-role deduplication and exact selection;
mock HTTP/checksum authentication, bounds, malformed/truncated/unsafe ZIP, redirects;
no network without explicit fetch; corrupt retained evidence and interrupted/no-clobber
resume; headed/headerless minute parsing, timestamp units/day/close alignment, exact
decimal sums and low ambient precision, shuffled/identical/conflicting rows, partial
hours, required-day/role coverage, product-specific quality gaps, differing row orders,
each comparison field and imbalance mismatch, missing/stale/wrong completion/schema/
lineage/hash, protected output paths, deterministic replay and FAILED-not-PASS behavior.

Under the targeted senior test exception, after the complete five-path drop is ready,
Grok may run exactly once:

```bash
PYTHONPATH=src .venv/bin/python -m pytest tests/acquisition/test_binance_usdm_kline_comparison_sample.py tests/ingest/test_binance_usdm_kline_reconciliation.py -q --tb=short
```

Stop on the first nonzero result; report exact output without repair/retry. No additional
syntax checks, Ruff, acceptance suite or real CLI execution. Return the five paths with
SHA-256/line counts, targeted result and limitations, then stop for reviewer inspection.
Source authoring does not accept real sample evidence. Integration, later real execution
and evidence remain separately bounded after source review. Existing ten accepted
products, holdout 2026-08-21T16:19:08.994166+00:00 and next ticket NONE remain unchanged.

## Reviewer publication scope

The reviewer may publish exactly this review, Review 487's final acceptance section,
`docs/handoff/CURRENT_TASK.md` and `tickets/CEX-002.md`. Wait for Hermes's three-path
Record 488 publication before staging reviewer governance, to avoid shared-index races.
Grok may author its five disjoint source paths while that record-only work finishes.
