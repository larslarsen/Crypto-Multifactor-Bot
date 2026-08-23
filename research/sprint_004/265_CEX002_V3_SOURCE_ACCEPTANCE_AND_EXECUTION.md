# CEX-002 V3 Source Acceptance and Execution

- **Date:** 2026-08-23
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** reviews 257-264 source/test correction accepted for integration and execution
- **Authorized actor:** Jr Dev - Hermes
- **Gate 2:** not accepted; v3 execution evidence pending
- **Next ticket:** `NONE`

## Accepted identities

The reviewer inspected the completed review-264 drop once at:

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py` | `d4afaa6285733c10311560b9fd68b223ab31fa90b1293a71871ea262daa82f5b` |
| `tests/acquisition/test_binance_usdm_harmonic_sizing.py` | `51029244dc068e85a3ec14381088ac05633047de8f7e8020e98bdafe673e197e` |
| `scripts/research/size_binance_usdm_harmonic_release.py` | `36740c926c32e4973bb31dcb570d3c69b89f9f343d52eb8aed3d33d359d7b23c` (unchanged) |

The test file has 161 `def test_` functions and the two edited files pass static diff
whitespace validation. The reviewer ran no pytest, Ruff, sizing, qualification, control,
network, or data-mutation command.

## Static acceptance

The v3 partition-aware allocation is accepted for execution. It preserves the complete
universe, products, economic rows/fields, cost sample, quality-gap ceiling, lineage,
reserve, immutable v1/v2 evidence, and accepted source authority while replacing repeated
dictionary values and whole-tree temporary copies with the actual partition layout. It
measures and publishes the real five-column shared identity anchor, keeps current null
validity disjoint from future indices/values, sizes every accepted identity class and
Coinalyze mapping, retains actual row-group cardinality, and publishes recomputable exact
and conservative largest-partition facts.

One internal `_exact` diagnostic label says `index` while checking the 14-byte current
identity total. Its compared values, stable receipt fields, allocation equations, and
tests distinguish 12 index, 2 current-null, and 14 total bytes correctly. It cannot affect
a successful result and is accepted as nonblocking diagnostic wording.

This is source acceptance only. It does not accept Gate 2 or authorize acquisition,
normalization, catalog publication, NautilusTrader, Harmonic Trader, or later work.

## Hermes integration and execution

Hermes owns exact-byte integration, validation and sizing commands, evidence publication,
Git commit, and push. Do not pull, reset, restore, checkout, stash, discard, or edit the
accepted developer source. Do not touch unrelated dirty work. Do not load `.env`, request
network access, acquire data, normalize a release, publish a catalog, or perform
NautilusTrader, Harmonic Trader, payoff, PAPER, LIVE, or next-ticket work.

### 1. Preproof and exact integration

Require `HEAD == origin/main`. Recompute the three accepted hashes and 161-function count;
stop on any mismatch. Confirm no sizing/qualification process is running, receipt 258 is
absent, the v3 sizing evidence directory contains no Parquet file, and the accepted
manifest detail exists at:

`data/cex002_qualify/evidence/manifests/sha256/d6c1fac650aaf16d88750da2a40d837f543d0c5fc88c73d463753a576d5bdd17.jsonl.gz`

Stage exactly the two modified sizing source paths. The CLI is already integrated and
byte-identical; do not rewrite it. Do not delete or rewrite v1/v2 receipts or envelopes.

### 2. Focused validation

Run once:

```bash
PYTHONDONTWRITEBYTECODE=1 timeout --signal=TERM --kill-after=60s 50m \
  .venv/bin/python -m pytest \
  tests/acquisition/test_binance_usdm_harmonic_sizing.py -q --tb=short \
  -k 'not test_the_real_accepted_authority_completes_the_receipt_path'
```

Then run:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m ruff check \
  src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py \
  tests/acquisition/test_binance_usdm_harmonic_sizing.py \
  scripts/research/size_binance_usdm_harmonic_release.py
```

If either exits nonzero or times out, stop before sizing and publish record 266 with every
failure. Do not repair or rerun.

### 3. First real v3 sizing invocation

Only after both validations pass, record start/end UTC and elapsed seconds and run once:

```bash
PYTHONDONTWRITEBYTECODE=1 timeout --signal=TERM --kill-after=60s 50m \
  .venv/bin/python scripts/research/size_binance_usdm_harmonic_release.py \
  --manifest-detail-path \
  data/cex002_qualify/evidence/manifests/sha256/d6c1fac650aaf16d88750da2a40d837f543d0c5fc88c73d463753a576d5bdd17.jsonl.gz
```

Record exit status, complete stderr, receipt SHA-256/size/schema, published/reused envelope
counts, storage state, every blocker, all six capacity components, total required bytes,
post-publication available bytes, and the v3 evidence manifest. A complete blocked receipt
with exit 0 is valid measurement evidence, not Gate-2 acceptance. A nonzero exit or timeout
stops immediately with no retry.

### 4. One idempotence invocation

Only after first-run exit 0, run the identical command exactly once more. Require exit 0,
the same receipt SHA-256 and byte length, zero new envelopes, complete reuse of the first
run's v3 envelope set, the same sorted evidence manifest, and no authority or v1/v2
mutation. Stop on any disagreement.

### 5. Evidence and publication

Write `research/sprint_004/266_CEX002_V3_SIZING_INTEGRATION_AND_EXECUTION.md` with exact
commands, timestamps, statuses, hashes, counts, receipt/capacity equations, evidence
manifest, and immutable-authority facts. Make no reviewer decision. Update
`docs/handoff/CURRENT_TASK.md` and `tickets/CEX-002.md` to require reviewer inspection,
with next ticket `NONE`.

Stage exactly:

1. the two accepted sizing source paths;
2. record 266;
3. receipt 258 only if validly produced;
4. `docs/handoff/CURRENT_TASK.md`; and
5. `tickets/CEX-002.md`.

Run `python3 scripts/check_repo_control.py` and `git diff --cached --check`. On success,
commit and push only those paths. V3 envelopes are ignored data evidence and never staged.
All unrelated dirty files remain untouched and unstaged. Stop for reviewer inspection; do
not accept Gate 2 or authorize acquisition.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly:

- `research/sprint_004/265_CEX002_V3_SOURCE_ACCEPTANCE_AND_EXECUTION.md`;
- `docs/handoff/CURRENT_TASK.md`; and
- `tickets/CEX-002.md`.

Developer source/test/CLI paths, receipts, evidence, and unrelated dirty work are excluded.
