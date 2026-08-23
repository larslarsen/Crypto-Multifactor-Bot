# CEX-002 V3 Ordering Source Acceptance and Execution

- **Date:** 2026-08-23
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** review-273 Sol High correction accepted for integration and execution
- **Authorized actor:** Jr Dev - Hermes
- **Gate 2:** not accepted; corrected execution evidence pending
- **Next ticket:** `NONE`

## Accepted identities

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py` | `d4afaa6285733c10311560b9fd68b223ab31fa90b1293a71871ea262daa82f5b` (unchanged) |
| `tests/acquisition/test_binance_usdm_harmonic_sizing.py` | `3b5acf85c5ee5aab891f9b9622e3cc7e86e0c2df2b630812f6f26e9bce20580a` |
| `scripts/research/size_binance_usdm_harmonic_release.py` | `36740c926c32e4973bb31dcb570d3c69b89f9f343d52eb8aed3d33d359d7b23c` (unchanged) |

The test file has exactly 161 functions and the diff passes static whitespace validation.
The only change moves the existing Coinalyze allocation assignment before its first use
and removes the later duplicate.

## Reviewer targeted result

After review 275 and the governing reviewer exception were committed and pushed, the
reviewer ran the exact authorized source-feedback command once:

```bash
PYTHONDONTWRITEBYTECODE=1 timeout --signal=TERM --kill-after=30s 10m \
  .venv/bin/python -m pytest \
  tests/acquisition/test_binance_usdm_harmonic_sizing.py -q --tb=short \
  -k 'test_the_v3_capacity_terms_reconcile_exactly'
```

Result: exit `0`, tool-reported wall time `1.587353247` seconds, one selected test passed.
This targeted result is source-review feedback only. It does not integrate the drop or
replace Hermes's focused validation, Ruff, sizing, evidence, records, or Git duties.

## Hermes integration and execution

Hermes owns exact integration, validation, sizing, evidence, records, Git, commit, and
push. Do not pull, reset, restore, checkout, stash, discard, or rewrite the accepted test.
Do not touch unrelated dirty work. Do not load `.env`, request network access, acquire
data, normalize, publish a catalog, or perform NautilusTrader, Harmonic Trader, payoff,
PAPER, LIVE, or next-ticket work.

### 1. Preproof and integration

Require `HEAD == origin/main`. Recompute the three accepted hashes and 161-function count;
stop on mismatch. Confirm no sizing/qualification process is running, receipt 258 is
absent, v3 sizing evidence contains no Parquet file, and the accepted manifest detail
exists at:

`data/cex002_qualify/evidence/manifests/sha256/d6c1fac650aaf16d88750da2a40d837f543d0c5fc88c73d463753a576d5bdd17.jsonl.gz`

Stage exactly the accepted sizing test path. Production and CLI are already integrated and
byte-identical; do not rewrite or stage them. Do not delete or rewrite v1/v2 evidence.

### 2. Full focused validation and Ruff

Run once:

```bash
PYTHONDONTWRITEBYTECODE=1 timeout --signal=TERM --kill-after=60s 50m \
  .venv/bin/python -m pytest \
  tests/acquisition/test_binance_usdm_harmonic_sizing.py -q --tb=short \
  -k 'not test_the_real_accepted_authority_completes_the_receipt_path'
```

Then run once:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m ruff check \
  src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py \
  tests/acquisition/test_binance_usdm_harmonic_sizing.py \
  scripts/research/size_binance_usdm_harmonic_release.py
```

If either exits nonzero or times out, stop before sizing and publish record 277 with every
failure. Do not repair or rerun.

### 3. First real v3 sizing invocation

Only after both validations pass, record start/end UTC and elapsed seconds and run once:

```bash
PYTHONDONTWRITEBYTECODE=1 timeout --signal=TERM --kill-after=60s 50m \
  .venv/bin/python scripts/research/size_binance_usdm_harmonic_release.py \
  --manifest-detail-path \
  data/cex002_qualify/evidence/manifests/sha256/d6c1fac650aaf16d88750da2a40d837f543d0c5fc88c73d463753a576d5bdd17.jsonl.gz
```

Record exit status, stderr, receipt SHA-256/size/schema, published/reused envelope counts,
storage state, every blocker, all six capacity components, total required bytes,
post-publication available bytes, and the sorted v3 evidence manifest. A complete blocked
receipt with exit 0 is valid measurement evidence, not Gate-2 acceptance. A nonzero exit
or timeout stops immediately with no retry.

### 4. One idempotence invocation

Only after first-run exit 0, run the identical sizing command once more. Require exit 0,
the same receipt SHA-256 and byte length, zero new envelopes, complete reuse of the first
run's v3 envelopes, the same sorted evidence manifest, and no authority or v1/v2 mutation.
Stop on any disagreement.

### 5. Evidence and publication

Write `research/sprint_004/277_CEX002_V3_ORDERING_INTEGRATION_AND_EXECUTION.md` with exact
commands, timestamps, statuses, hashes, counts, receipt/capacity equations, evidence
manifest, and immutable-authority facts. Make no reviewer decision. Update current task
and ticket to require reviewer inspection with next ticket `NONE`.

Stage exactly the accepted test, record 277, receipt 258 only if validly produced,
`docs/handoff/CURRENT_TASK.md`, and `tickets/CEX-002.md`. Run repository control and cached
diff whitespace validation. On success, commit and push only those paths. V3 envelopes are
ignored evidence and never staged. Stop for reviewer inspection; do not accept Gate 2 or
authorize acquisition.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly this record, current task, and ticket.
Developer test source, receipt, evidence, and unrelated dirty work are excluded.
