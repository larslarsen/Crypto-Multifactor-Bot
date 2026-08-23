# CEX-002 V2 Receipt Boundary Acceptance and Execution

- **Date:** 2026-08-23
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** review-248 correction accepted for integration and execution
- **Authorized actor:** Jr Dev - Hermes
- **Gate 2:** not accepted; execution evidence pending
- **Next ticket:** `NONE`

## Accepted identities

The reviewer inspected Claude Build's complete review-248 correction once at:

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py` | `32153fe509929eedd64731f57046eb0cc838cb3296ea681e195481358af694bc` |
| `tests/acquisition/test_binance_usdm_harmonic_sizing.py` | `6a9fdb3103f9259545864d5341a1d61739df15e9669b2a325fa8a615cae327a3` |
| `scripts/research/size_binance_usdm_harmonic_release.py` | `36740c926c32e4973bb31dcb570d3c69b89f9f343d52eb8aed3d33d359d7b23c` (unchanged) |

The test file contains 139 `def test_` functions. No reviewer pytest, Ruff, sizing,
qualification, control, acceptance, network, or data command was run.

## Static acceptance

Review 248 is closed in one pass:

- the successful first-publication path canonicalizes and decodes the final self-sized
  receipt before both publication and return, so its public mapping is the exact durable
  JSON document rather than a tuple-bearing pre-serialization equivalent;
- receipt canonical bytes, digest, byte length, self-length, capacity decision, and all
  facts remain governed by the same canonical encoder;
- a valid rerun still returns the independently decoded and revalidated prior, and tests
  now require the first result, second result, and decoded durable target to be equal;
- all five ADR-0026 cost components identify required product
  `binance_usdm_cost_calibration` plus their own component name;
- the fixed-schema, coverage-authority, and cost-component views receive the same
  fee-gap/scenario/official identities without inventing an additional required product;
- standalone fixed-schema products keep their existing identities; and
- stable projection, prior internal wholeness, semantic envelope counts, six-component
  capacity arithmetic, retained lineage, tamper, collision, no-follow, race,
  content-addressed publication, and v1 immutability remain intact.

This is source acceptance only. It does not accept Gate 2 or authorize acquisition,
normalization, catalog publication, NautilusTrader, Harmonic Trader, or later work.

## Hermes integration and execution

Hermes owns exact-byte integration, validation and sizing commands, evidence publication,
Git commit, and push. Do not pull, reset, restore, checkout, stash, discard, or edit the
accepted developer source. Do not touch unrelated dirty work. Do not load `.env`, request
network access, acquire data, normalize a release, publish a catalog, or perform
NautilusTrader, Harmonic Trader, payoff, PAPER, LIVE, or next-ticket work.

### 1. Preproof and exact integration

Require `HEAD == origin/main` at this review publication. Recompute the three accepted
hashes and the 139-function count; stop on any mismatch. Stage exactly the two modified
sizing paths. The CLI is already integrated and byte-identical; do not rewrite it.

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
failure record with every reported failure.

### 3. First real v2 sizing invocation

Only after both validations pass, record start UTC and run once without `.env` or network:

```bash
PYTHONDONTWRITEBYTECODE=1 timeout --signal=TERM --kill-after=60s 50m \
  .venv/bin/python scripts/research/size_binance_usdm_harmonic_release.py \
  --manifest-detail-path \
  data/cex002_qualify/evidence/manifests/sha256/d6c1fac650aaf16d88750da2a40d837f543d0c5fc88c73d463753a576d5bdd17.jsonl.gz
```

Record end UTC, elapsed seconds, exit status, complete stderr, receipt identity and size,
envelope published/reused counts, storage state, every blocker, all six capacity
components, total required bytes, and post-publication available bytes. A complete
`blocked` receipt with exit 0 is valid measurement evidence, not Gate-2 acceptance.

If this invocation exits nonzero or times out, stop immediately and do not retry.

### 4. One idempotence invocation

Only if the first invocation exits 0, record start/end UTC and run the identical command
exactly once more. Require exit 0, the same receipt SHA-256 and byte length, zero newly
published envelopes, the same complete v2 evidence manifest, and no authority mutation.
Stop on any disagreement.

### 5. Evidence and publication

Write `research/sprint_004/250_CEX002_V2_SIZING_FINAL_INTEGRATION_AND_EXECUTION.md`
with exact commands, timestamps, statuses, hashes, counts, receipt facts, capacity
equations, and pre/post authority and v1-immutability evidence. Make no reviewer decision.

Update `docs/handoff/CURRENT_TASK.md` and `tickets/CEX-002.md` to require reviewer
inspection, with next ticket `NONE`. Include receipt 231 only if it was validly produced.
Stage exactly:

1. the two accepted modified sizing paths;
2. `research/sprint_004/250_CEX002_V2_SIZING_FINAL_INTEGRATION_AND_EXECUTION.md`;
3. `research/sprint_004/231_CEX002_GATE2_STORAGE_SIZING_V2.json` only if valid;
4. `docs/handoff/CURRENT_TASK.md`; and
5. `tickets/CEX-002.md`.

Run `python3 scripts/check_repo_control.py` and `git diff --cached --check`. On success,
commit and push only those exact paths. V2 envelopes are ignored data evidence and are
never staged. All unrelated dirty files remain untouched and unstaged. Stop for reviewer
inspection; do not accept Gate 2 or authorize acquisition.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly:

- `research/sprint_004/249_CEX002_V2_RECEIPT_BOUNDARY_ACCEPTANCE_AND_EXECUTION.md`;
- `docs/handoff/CURRENT_TASK.md`; and
- `tickets/CEX-002.md`.

Developer source/test/CLI paths and unrelated dirty work are excluded.
