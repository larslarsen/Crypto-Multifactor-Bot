# CEX-002 Review 429 — Record 428 Acceptance and Midnight-Spillover Correction

- **Date:** 2026-09-01
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** accept the terminal record; preserve the filename contract-day as authority; authorize one bounded source/test correction
- **Gate 2:** `ACCEPTED`
- **Gate 3:** `IN_PROGRESS`
- **Next required actor:** Sr Dev — Codex Sol
- **Next ticket:** `NONE`

## Record 428 acceptance

`HEAD == origin/main == 256867016ef9f86cb8a127fdfb22bb096c704367`. Record 428 accurately
states the sole Review-427 runner's terminal error and the preserved hidden output. The runner
exited 1 after approximately 4 minutes 39 seconds. The eight existing 0GUSDT Parquet/lineage
pairs remain unreferenced evidence because no completion descriptor exists. They are neither
deleted nor accepted as a product.

This failure does not reopen Gate 2 and is not an acquisition blocker. All accepted raw source
objects remain available and authenticated. It is a normalization source-contract defect.

## Exact read-only diagnosis

The first and only out-of-contract-day row found across all 336 accepted 0GUSDT daily metrics
objects is in:

`data/futures/um/daily/metrics/0GUSDT/0GUSDT-metrics-2026-05-03.zip`

It is a generation-0 `retained_credit` object of 10,041 bytes at accepted SHA-256
`dec4ce5ab806eeeb8d80632c894314d369b5ed0f2d0a7d750c45e6c70329d946`. The object has 288
data rows. Original row ordinals 0 through 286 cover the 287 five-minute points from
`2026-05-03 00:05:00` through `23:55:00`. Original ordinal 287 is the next UTC midnight:

```text
2026-05-04 00:00:00,0GUSDT,16214085.0000000000000000,8620002.1564969500000000,0.82603816,1.00049200,0.64963271,0.31879700
```

The accepted v3 object named for 2026-05-04 exists separately at SHA-256
`1273db2682e7af6c753a57cf09e0d4daf34985636c5c6f2096f5189b9d9d9d08` and contains a
different observation at its own 00:00 boundary:

```text
2026-05-04 00:00:00,0GUSDT,16208689.0000000000000000,8586781.3781780100000000,0.83164414,1.00019100,0.66076601,0.20487700
```

Therefore timestamp reassignment or last-row-wins deduplication would silently choose between
conflicting market values. The canonical archive filename remains the contract-day authority.
The May-03 spillover row cannot overwrite or compete with the May-04-owned observation. The
missing May-03 00:00 grid point remains missing and must be emitted by the existing typed
quality-gap logic.

## Bounded correction authorized

Sr Dev — Codex Sol on GPT-5.6-sol High may edit exactly:

- `src/cryptofactors/ingest/binance_usdm_open_interest.py`; and
- `tests/ingest/test_binance_usdm_open_interest.py`.

The normalizer must continue to fully parse and validate every physical row, including symbol,
timestamp/grid, and every decimal field. A row outside its source contract-day may be excluded
from normalized product rows only when all of these fail-closed conditions hold:

1. its timestamp is exactly `00:00:00 UTC` on the calendar day immediately after the canonical
   source filename date;
2. it is the sole excluded row in that source object; and
3. at least one fully valid in-contract-day row remains in that source object.

Any preceding-day row, non-midnight following-day row, later date, second excluded row, invalid
field, or all-excluded source still fails normalization. The physical object remains bounded to
288 rows. Excluded rows are never reassigned to another date, emitted as product rows, used for
stock/change calculations, or allowed to suppress or replace the observation owned by the next
day's source object.

For every accepted exclusion, the affected partition lineage must add a deterministic
`excluded_source_rows` fact containing at least the raw source key and SHA-256, original
`source_row_ordinal`, expected contract-day, observed UTC timestamp, and a fixed reason. The field
must be omitted when empty so the eight already published unaffected lineage documents remain
byte-identical and reusable. The final completion totals must state the exact excluded-row count.
The existing inferred quality-gap artifact must expose the omitted May-03 `00:00` observation;
no value may be imputed. Existing raw-object lineage, duplicate/conflict rejection, sorting,
five-minute continuity, stock/change, gap, and atomic publication behavior remain unchanged.

The focused test source must prove all of the following in one owned-boundary regression:

- a prior-day `23:55`, a source-day beginning at `00:05` with one next-midnight spillover, and a
  next-day-owned conflicting `00:00` observation;
- the spillover does not appear in product rows and the next-day-owned value does;
- original row ordinal and raw source identity are present in the affected partition's exclusion
  lineage;
- the source-day `00:00` point is present as an inferred typed missing-grid gap; and
- the final descriptor reports exactly one excluded source row.

Focused rejection coverage must prove that a non-midnight or non-adjacent out-of-day timestamp
still fails. Existing tests must continue to pass.

Sol may run exactly once after editing:

```bash
.venv/bin/python -m pytest tests/ingest/test_binance_usdm_open_interest.py -q --tb=short
```

Sol stops on a nonzero result without patching or rerunning and otherwise stops for reviewer
inspection with exact hashes and line counts. No CLI edit, real-data invocation, hidden-output
mutation, cleanup, retry, runner, integration, record/control edit, Git operation, network,
acquisition, other product, experiment, model, trading-engine work, or next ticket is authorized.

Under the AGENTS.md reviewer governance-publication exception this review commits and pushes
exactly:

- `research/sprint_004/429_CEX002_RECORD428_ACCEPTANCE_AND_MIDNIGHT_SPILLOVER_CORRECTION.md`;
- `docs/handoff/CURRENT_TASK.md`; and
- `tickets/CEX-002.md`.

All developer, partial-output, runner-evidence, and unrelated dirty paths remain untouched.
