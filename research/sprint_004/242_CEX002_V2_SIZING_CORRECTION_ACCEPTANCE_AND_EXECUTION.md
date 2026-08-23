# CEX-002 V2 Sizing Correction Acceptance and Execution

- **Date:** 2026-08-23
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** review-241 correction accepted for integration and execution
- **Authorized actor:** Jr Dev - Hermes
- **Gate 2:** not accepted; execution evidence pending
- **Next ticket:** `NONE`

## Accepted identities

The reviewer inspected Claude Build's complete review-241 correction once at:

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py` | `7ca6082f9c52f4d6b5a770647ecd452cea8c279faa41811ad31d7fc70f44b4c9` |
| `tests/acquisition/test_binance_usdm_harmonic_sizing.py` | `1867f9d271a1d4e04eab931209a08451a948938e5df42ad8619c1c1d062cc0a4` |
| `scripts/research/size_binance_usdm_harmonic_release.py` | `36740c926c32e4973bb31dcb570d3c69b89f9f343d52eb8aed3d33d359d7b23c` (unchanged) |

The test file contains 138 `def test_` functions. No reviewer pytest, Ruff, sizing,
qualification, control, acceptance, network, or data command was run.

## Static acceptance

The complete record-240 failure set is corrected in one drop:

- `build_retained_archive_bindings` now requires an exact positive retained checkpoint
  byte length and compares an accepted sample length to that retained length, while the
  separate requirement-listing length remains sourced from `PhysicalObject.byte_size`;
- the projected archive manifest continues to serialize the requirement-listing length;
- the exact retained-credit key, hash, checksum, retrieval, availability, and full-set
  joins are unchanged;
- an explicit test proves a 145-byte retained witness against an independent 2,072-byte
  requirement listing and rejects missing, non-integer, non-positive, or mismatched
  retained lengths;
- premium contribution scope, daily-plus-monthly 2/2/6 manifest mappings, exact decimal
  error text, shared identity/index fields, fixture-derived fee-gap count, and accepted
  alias decomposition are corrected; and
- directly adjacent schema-field assertions now compare declared field names rather than
  fixture row values.

No test was deleted or skipped. The production correction is narrowly confined to the
retained-byte authority boundary. All accepted review-237 through review-239 semantics
remain required. This is source acceptance only; it does not accept Gate 2 or authorize
acquisition or later work.

## Hermes integration and execution

Hermes owns exact-byte integration, validation and sizing commands, evidence publication,
Git commit, and push. Do not pull, reset, restore, checkout, stash, discard, or edit the
accepted developer source. Do not touch unrelated dirty work. Do not load `.env`, request
network access, acquire data, normalize a release, publish a catalog, or perform Harmonic
Trader, NautilusTrader, payoff, PAPER, LIVE, or next-ticket work.

### 1. Preproof and exact integration

Require `HEAD == origin/main` at this review publication. Recompute the three accepted
hashes and the 138-function count; stop on any mismatch. Stage exactly the two modified
sizing paths. The accepted CLI is already integrated and byte-identical; do not rewrite
it.

Confirm no sizing or qualification process is running, receipt 231 is absent, the v2
evidence directory has no Parquet file, and the accepted manifest detail exists at:

`data/cex002_qualify/evidence/manifests/sha256/d6c1fac650aaf16d88750da2a40d837f543d0c5fc88c73d463753a576d5bdd17.jsonl.gz`

Do not delete or rewrite any v1 receipt or v1 envelope.

### 2. Focused validation

Run once:

```bash
PYTHONDONTWRITEBYTECODE=1 timeout --signal=TERM --kill-after=60s 50m \
  .venv/bin/python -m pytest \
  tests/acquisition/test_binance_usdm_harmonic_sizing.py -q --tb=short \
  -k 'not test_the_real_accepted_authority_completes_the_receipt_path'
```

The deselected test invokes the same real sizing path twice. Steps 3 and 4 provide those
two real passes, so do not duplicate them inside pytest.

Then run exact-path Ruff:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m ruff check \
  src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py \
  tests/acquisition/test_binance_usdm_harmonic_sizing.py \
  scripts/research/size_binance_usdm_harmonic_release.py
```

If either command exits nonzero or times out, stop before sizing and publish one complete
failure record, including every reported failure rather than routing another piecemeal
source review.

### 3. First real v2 sizing invocation

Only after both validations pass, run once without `.env` or network:

```bash
PYTHONDONTWRITEBYTECODE=1 timeout --signal=TERM --kill-after=60s 50m \
  .venv/bin/python scripts/research/size_binance_usdm_harmonic_release.py \
  --manifest-detail-path \
  data/cex002_qualify/evidence/manifests/sha256/d6c1fac650aaf16d88750da2a40d837f543d0c5fc88c73d463753a576d5bdd17.jsonl.gz
```

Record start/end UTC, elapsed seconds, exit status, complete stderr, receipt identity and
size, envelope published/reused counts, storage state, every blocker, all six capacity
components, total required bytes, and post-publication available bytes. A complete
`blocked` receipt with exit 0 is valid measurement evidence, not Gate-2 acceptance.

If this invocation exits nonzero or times out, stop immediately and do not retry.

### 4. One idempotence invocation

Only if the first invocation exits 0, run the identical command exactly once more. Require
exit 0, the same receipt SHA-256 and byte length, zero newly published envelopes, the same
complete v2 evidence manifest, and no authority mutation. Stop on any disagreement.

### 5. Evidence and publication

Write `research/sprint_004/243_CEX002_V2_SIZING_CORRECTION_INTEGRATION_AND_EXECUTION.md`
with exact commands, timestamps, statuses, hashes, counts, receipt facts, capacity
equations, and pre/post authority and v1-immutability evidence. Make no reviewer decision.

Update `docs/handoff/CURRENT_TASK.md` and `tickets/CEX-002.md` to require reviewer
inspection, with next ticket `NONE`. Include receipt 231 only if it was validly produced.
Stage exactly:

1. the two accepted modified sizing paths;
2. `research/sprint_004/243_CEX002_V2_SIZING_CORRECTION_INTEGRATION_AND_EXECUTION.md`;
3. `research/sprint_004/231_CEX002_GATE2_STORAGE_SIZING_V2.json` only if valid;
4. `docs/handoff/CURRENT_TASK.md`; and
5. `tickets/CEX-002.md`.

Run `python3 scripts/check_repo_control.py` and `git diff --cached --check`. On success,
commit and push only those exact paths. V2 envelopes are ignored data evidence and are
never staged. All unrelated dirty files remain untouched and unstaged. Stop for reviewer
inspection; do not accept Gate 2 or authorize acquisition.

## Reviewer publication scope

Under the AGENTS.md reviewer exception, the reviewer may stage, commit, and push exactly:

- `research/sprint_004/242_CEX002_V2_SIZING_CORRECTION_ACCEPTANCE_AND_EXECUTION.md`;
- `docs/handoff/CURRENT_TASK.md`; and
- `tickets/CEX-002.md`.

Developer source/test/CLI paths and all unrelated dirty work are excluded.
