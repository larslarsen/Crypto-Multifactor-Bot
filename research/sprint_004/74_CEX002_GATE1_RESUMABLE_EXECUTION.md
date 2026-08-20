# CEX-002 Gate 1 Resumable Execution Record

Date: 2026-08-20

Actor: Jr Dev — Hermes

## Outcome

**BOTH REAL RUNS EXITED 2 (HONEST BLOCKED MATRIX). REQUIRED SEMANTIC RESUME IDENTITY CHECK FAILED.**

Per review 73, every real-run outcome returns the next actor to the reviewer. The two
bounded real qualification/resume runs completed against the preserved store, but the
mandatory assertion that the second (resumed) report is semantically identical to the
first after dropping volatility fields did not hold. No Gate 1 data acceptance is claimed.

## Reviewed identities (verified before execution)

Committed control-plane base: `HEAD == origin/main == 3e1468794c2e986b19606b35334ab9edfb6f9b6b`.

| Path | Expected (review 73) | Observed |
|---|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `3e8d14887f0f9e273a3fc00c3fd1b5d640cf01ad4214049a050df8425a5480d0` | `3e8d14887f0f9e273a3fc00c3fd1b5d640cf01ad4214049a050df8425a5480d0` |
| `scripts/research/qualify_binance_usdm_harmonic_sources.py` | `40d944a8149e22cd917fa3097009c53307bc5c9614ef35139f4317b1843e6f8a` | `40d944a8149e22cd917fa3097009c53307bc5c9614ef35139f4317b1843e6f8a` |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `c32b74f543c9254c81579a0275364b943a262c35f3b72050fa9560dbc7abdb90` | `c32b74f543c9254c81579a0275364b943a262c35f3b72050fa9560dbc7abdb90` |

All three observed hashes match review 73 exactly. The preserved store was intact before
execution: `data/cex002_qualify` at approximately 691 MiB with `fapi_cache`, `list_cache`,
and `raw` present.

## Command sequence (review 73 order)

### 1. Focused CEX-002 suite — PASS

`.venv/bin/python -m pytest tests/acquisition/test_binance_usdm_harmonic_qualification.py -q --tb=short`

79 passed, exit 0. This includes the corrected abort/resume, completed-key no-refetch,
distinct-bytes missing-fetch, semantic-identity, and same-digest cross-key recovery tests.

### 2. Atomic-download suite — PASS

`.venv/bin/python -m pytest tests/test_download_atomicity.py -q --tb=short`

11 passed, exit 0.

### 3. Ruff — PASS

`.venv/bin/python -m ruff check src/cryptofactors/ scripts/`

All checks passed, exit 0.

### 4. Repository control — PASS

`python3 scripts/check_repo_control.py`

Repo control check: PASS.

### 5. Diff check — PASS

`git diff --check`

No output, exit 0.

## Integration commit

After all five commands passed, Hermes staged exactly the three reviewed source/test paths,
verified `git diff --cached --name-only` listed only:

- `scripts/research/qualify_binance_usdm_harmonic_sources.py`
- `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py`
- `tests/acquisition/test_binance_usdm_harmonic_qualification.py`

Committed with message `CEX-002: integrate resumable bounded Gate 1 qualifier` at
`70ded4591ebb692e2b0fe223c6aa52d2207b30c0` and pushed so
`HEAD == origin/main == 70ded4591ebb692e2b0fe223c6aa52d2207b30c0` before network
execution.

## Real run 1

Command (authorized verbatim):

```
/bin/bash -lc 'set -a; . ./.env; set +a; .venv/bin/python scripts/research/qualify_binance_usdm_harmonic_sources.py --store-root data/cex002_qualify --progress-path data/cex002_qualify/cex002_qualification_progress.json --report-path /tmp/cex002_gate1_resumable_first.json'
```

The run required four invocations. The first was killed by a 60-minute tool timeout, the
second by a user abort, and the third by a six-hour tool timeout; each made partial
progress and was resumed on the same store and progress file. The final detached
invocation (pid 3290575) ran continuously for 25h22m and completed.

- Report: `/tmp/cex002_gate1_resumable_first.json`, SHA-256
  `43f0c51a5f18bf1dc03ff654aacdca95ec5f4c6fb42c07102f6e2d104d5137c6`
- Report `generated_at` (run start): `2026-08-19T10:18:04.572443+00:00`; file written
  2026-08-20 04:40 local.
- Exit code: **2** (`qualification_exit_code` returns 2 unless `accepted` and
  `gate_status == QUALIFIED`).
- `gate_status=BLOCKED accepted=False symbols=1004`
- Blocked products (8): `binance_usdm_trade`, `binance_usdm_bar_1m`,
  `binance_usdm_open_interest_5m`, `binance_usdm_funding_realized`,
  `binance_usdm_funding_indicative`, `binance_usdm_mark_index_basis`,
  `binance_usdm_liquidation_observed`, `binance_usdm_cost_calibration`.
- Storage: full-family exact object/byte totals (not extrapolated), 20 physical families
  inventoried, `discovered_symbol_count=1004`. Selected exact counts:
  `binance_usdm_perpetual_membership` 1,004 objects /
  6,628,196,148,904 bytes; `binance_usdm_trade` 1,297,467 / 6,174,436,174,147;
  `binance_usdm_bar_1m` 709,650 / 61,196,652,414; `binance_usdm_open_interest_5m`
  595,471 / 6,291,378,762; `binance_usdm_funding_realized` 21,425 / 21,645,197;
  `binance_usdm_funding_indicative` 660,936 / 28,705,337,062;
  `binance_usdm_mark_index_basis` 2,067,175 / 99,853,687,857;
  `binance_usdm_cost_calibration` 584,222 / 2,448,204,498,577;
  `binance_usdm_liquidation_observed`, `binance_usdm_trade_flow`,
  `binance_usdm_harmonic_bundle`, `binance_usdm_coverage_gap` 0 objects.
- Sample plan: `planned_new_bytes=266836686`, `budget=268435456`,
  `retained_bytes=702723924`, `budget_blocked=7`.
- Listing checkpoint: `reused=17984 fetched=21821 unclaimed=0`, `retries=43`.
- Retry journal: `attempts=22221`, 14 incidents (all `DownloadError`, retryable,
  `status_code=None`).
- Resume: `progress_objects=183`, `recovered_samples=6`, `reused_samples=6`,
  `rehash_required=True`.
- Coinalyze: `key_present=true`, `qualified=false` — history symbols do not match request
  (`/liquidation-history`, requested `0GUSDT_PERP.A` and `IOSTUSDT_PERP.A`, returned
  `IOSTUSDT_PERP.A`).

## Real run 2

Command (authorized verbatim, report path changed):

```
/bin/bash -lc 'set -a; . ./.env; set +a; .venv/bin/python scripts/research/qualify_binance_usdm_harmonic_sources.py --store-root data/cex002_qualify --progress-path data/cex002_qualify/cex002_qualification_progress.json --report-path research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json'
```

A single detached invocation completed in approximately 8 minutes.

- Report: `research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json`, SHA-256
  `ddedc886f229bfb51b9eb516490654f50a24a72a5a11ec9b95142f56ed3cdc85`
- Report `generated_at` (run start): `2026-08-20T12:01:46.524397+00:00`; file written
  2026-08-20 05:09 local.
- Exit code: **2** (same BLOCKED matrix).
- `gate_status=BLOCKED accepted=False symbols=1004`; identical 8 blocked products.
- Storage: byte-for-byte identical full-family totals to run 1.
- Sample plan: `planned_new_bytes=30367993`, `budget=268435456`,
  `retained_bytes=969560610`, `budget_blocked=4`.
- Listing checkpoint: `reused=39805 fetched=0 unclaimed=0`, `retries=0` — full reuse, no
  new listing fetches.
- Retry journal: `attempts=9`, 0 incidents, 0 retries.
- Resume: `progress_objects=278`, `recovered_samples=92`, `reused_samples=196`.
- Coinalyze: identical `qualified=false` symbol-mismatch reason.

## Semantic resume identity check — FAILED

Required command (authorized verbatim):

```
.venv/bin/python -c 'import json; from pathlib import Path; from cryptofactors.acquisition.binance_usdm_harmonic_qualification import drop_identity_volatility; a=json.loads(Path("/tmp/cex002_gate1_resumable_first.json").read_text()); b=json.loads(Path("research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json").read_text()); assert drop_identity_volatility(a)==drop_identity_volatility(b); print("Gate 1 semantic resume identity: PASS")'
```

Result: `AssertionError` at the equality assertion. The expected `PASS` was not printed.

The two reports are not semantically identical after dropping identity/volatility fields.
Divergent top-level keys: `incidents`, `product_matrix`, `resume`, and `samples`.

- `samples`: run 1 has 196 sample records; run 2 has 199. The object keys, provider
  checksums, symbols, families, schemas (`headed`/`headerless`), and byte sizes differ for
  a large contiguous block (run 1 sampled `monthly/trades` and `daily/aggTrades` for
  ZRXUSDT/IOSTUSDT/1000BTTCUSDT/0GUSDT; run 2 sampled a different complementary set,
  e.g. `monthly/aggTrades` for 0GUSDT/IOSTUSDT/ZRXUSDT/1000BTTCUSDT).
- `sample_plan`: run 1 `planned_new_bytes=266836686`, run 2 `30367993`; budget-remaining
  accounting differs (run 2 reports full `268435456` remaining per blocked entry because
  its new downloads were planned after run 1 consumed the budget).
- `product_matrix`: per-product `sample_count` differs (e.g. 171 vs 174 and 48 vs 51) and
  `sample_budget_blocked` budget-remaining values differ.
- `resume`: `progress_objects` 183 vs 278; `recovered_samples` 6 vs 92; `reused_samples`
  6 vs 196.
- `incidents`: 14 vs 8.

Interpretation: the Gate 1 sample selection is a greedy budget-constrained plan over the
currently retained store. Run 1 consumed the 256 MiB new-download budget across a large
first sample set (196 samples, 183 retained blobs). The resumed run therefore plans a
different, complementary sample set (reusing 196 retained samples and downloading 3 more)
so that the retained sample evidence differs from the first run's. The resume is
functionally correct and safe (no unnecessary refetch, checksum/rehash evidence intact,
no duplicate economic objects), but it does **not** produce the semantically identical
report the review-73 acceptance contract requires for the two-run comparison.

## Integrity assertions

- The `.env` key was loaded only via `set -a; . ./.env; set +a` and never printed or
  placed in a command argument; no secret value appears in this record or the reports.
- `data/cex002_qualify` was never deleted, renamed, or replaced. Retained-store size:
  **4,432,891,470 bytes** (~4.1 GiB). Components: `list_cache` (largest), `raw` 186
  content-addressed blobs / 969 MiB, `cex002_listing_checkpoint.json` 23.7 MiB,
  `cex002_qualification_progress.json` 299 KB, `cex002_sample_plan.json` 105 KB,
  `cex002_retry_journal.json` 8.8 KB, `fapi_cache` 1.1 MB, `coinalyze_cache` (empty).
- Progress file identity: `data/cex002_qualify/cex002_qualification_progress.json`
  (299,571 bytes, written 2026-08-20 05:09). Listing checkpoint identity:
  `data/cex002_qualify/cex002_listing_checkpoint.json` (23,676,974 bytes, written
  2026-08-20 05:01). Sample-plan identity:
  `data/cex002_qualify/cex002_sample_plan.json` (105,884 bytes, written 2026-08-20
  05:08). Retry-journal identity: `data/cex002_qualify/cex002_retry_journal.json` (8,821
  bytes, written 2026-08-20 04:31).
- Both reports contain no secret material; the Coinalyze key presence is recorded only as
  `key_present: true`.

## Consequence

Gate 1 remains `IN_PROGRESS`. Both real runs exited 2 with an honest blocked matrix, and
the required semantic resume identity check failed. The reviewer must disposition the
budget-dependent sample-selection divergence before any further execution. Per review 73,
the next required actor is set to the reviewer.