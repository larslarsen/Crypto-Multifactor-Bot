# CEX-002 Review 426 — Record 425 Acceptance and Daily-Row Order Correction

- **Date:** 2026-09-01
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** accept the terminal record; identify the exact real-data assumption; authorize one bounded source/test correction
- **Gate 2:** `ACCEPTED`
- **Gate 3:** `IN_PROGRESS`
- **Next required actor:** Sr Dev — Codex Sol
- **Next ticket:** `NONE`

## Record 425 acceptance

`HEAD == origin/main == 85965e9294612123c1b762ad8ba63cfef82a5ed6`. Record 425 SHA-256
is `37a19210af205b9c128bea1945bf91b67213b28babf01615d257267fb0229426`. The exact
three-path publication accurately records the sole Review-424 runner, its captured traceback,
the status-poll race, and the partial hidden output. The seven Parquet/lineage pairs are
unreferenced evidence because no completion descriptor exists; no product is accepted.

## Exact read-only diagnosis

The first offending raw identity is:

`data/futures/um/daily/metrics/0GUSDT/0GUSDT-metrics-2026-04-23.zip`

It is an accepted v3 direct-recovery object of 10,692 bytes with both accepted and observed
SHA-256 `d3869d4297f5fe4189e243c28d3e73db0139abc860313de76fbcf859b8b3f370`.
A reviewer read-only parse proves:

- one expected CSV member;
- 288 data rows and 288 unique timestamps;
- a complete five-minute grid from `2026-04-23 00:00:00` through `23:55:00`;
- no missing point and no duplicate timestamp; and
- shuffled physical CSV order.

The first reversal is physical data row 9 at `11:55:00` followed by row 10 at `00:55:00`.
The normalizer preserves physical row order and therefore rejects a valid, complete provider file
before it can apply its duplicate and continuity logic. The raw data and acquisition authority are
sound. CSV physical order is not an economic ordering guarantee.

## Bounded correction authorized

Sr Dev — Codex Sol on GPT-5.6-sol High may edit exactly:

- `src/cryptofactors/ingest/binance_usdm_open_interest.py`; and
- `tests/ingest/test_binance_usdm_open_interest.py`.

For each already authenticated daily source object, the normalizer must fully parse and validate
its rows, retain every original `source_row_ordinal`, sort the parsed rows by `create_time` before
the existing cross-row stock/change/gap logic, and continue to reject both identical and
conflicting duplicate timestamps. It must not change, aggregate, impute, drop, or rewrite any raw
value. Source objects remain ordered by symbol/date as now.

Because one UTC contract-day on a five-minute grid has exactly 288 possible timestamps, replace
the two-million-row per-object parser ceiling with an explicit 288-row daily grid bound. The ZIP
byte, decompression, field, source-date, timestamp-grid, decimal, duplicate, lineage, and
publication checks remain unchanged.

The focused test must provide a shuffled daily row sequence, prove output is timestamp-ordered,
prove original physical ordinals are preserved in the reordered output, and prove stock/change
semantics follow economic time. Existing duplicate-conflict tests must continue to pass.

Sol may run exactly once after editing:

```bash
.venv/bin/python -m pytest tests/ingest/test_binance_usdm_open_interest.py -q --tb=short
```

Sol stops on a nonzero result without patching or rerunning and otherwise stops for reviewer
inspection with exact hashes and line counts. No CLI edit, real-data invocation, partial-output
mutation, cleanup, retry, runner, integration, record/control edit, Git, network, acquisition,
other product, experiment, model, trading-engine work, or next ticket is authorized.

Under the AGENTS.md reviewer governance-publication exception this review commits and pushes
exactly:

- `research/sprint_004/426_CEX002_RECORD425_ACCEPTANCE_AND_DAILY_ROW_ORDER_CORRECTION.md`;
- `docs/handoff/CURRENT_TASK.md`; and
- `tickets/CEX-002.md`.

All developer, partial-output, runner-evidence, and unrelated dirty paths remain untouched.
