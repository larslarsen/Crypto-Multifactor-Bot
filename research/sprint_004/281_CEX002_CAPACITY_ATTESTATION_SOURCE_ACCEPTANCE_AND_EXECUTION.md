# CEX-002 Capacity Attestation Source Acceptance and Execution

- **Date:** 2026-08-23
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** review-280 Sol High correction accepted for integration and execution
- **Authorized actor:** Jr Dev - Hermes
- **Gate 2:** not accepted; real capacity evidence pending
- **Next ticket:** `NONE`

## Accepted identities

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_capacity_attestation.py` | `34973e6f801ef3a16e82c3333c01fb1ee81fad357810bc28fdd5eaabf18995ec` |
| `scripts/research/attest_binance_usdm_harmonic_capacity.py` | `e5195b967d83f3f1ab336f342c512ce375e80dbc66f67cb754acc2b86244ead5` |
| `tests/acquisition/test_binance_usdm_capacity_attestation.py` | `09c9663613a4addf7080d5d84f0470926e4aa86915094b2c4d21d27e6ac73cf9` |

The test file has exactly 15 functions and the three paths pass static whitespace
validation. The accepted sizing source/test/CLI and receipt remain byte-identical at:

- sizing source `d4afaa6285733c10311560b9fd68b223ab31fa90b1293a71871ea262daa82f5b`;
- sizing test `3b5acf85c5ee5aab891f9b9622e3cc7e86e0c2df2b630812f6f26e9bce20580a`;
- sizing CLI `36740c926c32e4973bb31dcb570d3c69b89f9f343d52eb8aed3d33d359d7b23c`;
  and
- receipt 258 `3995a5072a7d84baecae677ceff6e1c7af9dd076daadec04a31717ffc8f16589`.

The reviewer ran no pytest, Ruff, control, attestation, network, or data-mutating command.

## Static acceptance

The correction is accepted for execution. The attestation source now freezes the exact
accepted v3 stable receipt and capacity fields and computes the canonical projection and
identity locally, while its tests prove byte equality with the accepted sizing boundary
and sensitivity to non-capacity authority mutation. The runtime no longer delegates that
authority to unauthenticated live sizing code.

Post-publication failure now atomically removes the authoritative output name by moving
the attempt back to its private staging name, fsyncs the directory, and only then removes
staging. Rollback and later staging-cleanup failures are distinct explicit errors. The
ordinary capacity-loss test proves complete cleanup; the injected rollback test proves a
failed rollback cannot masquerade as cleanup; and the injected staging-cleanup test
proves the authoritative name is already absent. Preserve all earlier accepted schema,
device, no-replace, capacity, self-identity, and synthetic end-to-end behavior.

A reviewer read-only observation found 290,346,287,104 bytes currently available on the
receipt/store/output device and no visible download process. This is not capacity evidence
and does not accept Gate 2. Only the transactional command below may produce the reviewable
observation.

## Hermes integration and execution

Hermes owns exact integration, focused validation, the real attestation, evidence record,
Git, commit, and push. Do not pull, reset, restore, checkout, stash, discard, or rewrite
the accepted drop. Do not touch unrelated dirty work. Do not load `.env`, request network
access, acquire or normalize market data, publish a catalog, or perform NautilusTrader,
Harmonic Trader, payoff, PAPER, LIVE, or next-ticket work.

### 1. Exact preproof and integration

Require `HEAD == origin/main == ee3f9d760466662454571081e7571b5eb33b71b7`.
Recompute all seven hashes above and the 15-function count; stop on any mismatch. Confirm
no CEX-002 sizing or capacity-attestation process is running and this output is absent:

`research/sprint_004/282_CEX002_GATE2_CAPACITY_ATTESTATION.json`

Stage exactly the three accepted capacity-attestation paths. Do not rewrite them and do
not stage or alter any accepted sizing path, receipt 258, v3 envelope, or unrelated file.

### 2. Focused validation and Ruff

Run once:

```bash
PYTHONDONTWRITEBYTECODE=1 timeout --signal=TERM --kill-after=30s 10m \
  .venv/bin/python -m pytest \
  tests/acquisition/test_binance_usdm_capacity_attestation.py -q --tb=short
```

Then run once:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m ruff check \
  src/cryptofactors/acquisition/binance_usdm_capacity_attestation.py \
  scripts/research/attest_binance_usdm_harmonic_capacity.py \
  tests/acquisition/test_binance_usdm_capacity_attestation.py
```

If either command exits nonzero or times out, stop before the real attestation. Do not
repair or rerun. Continue only to the failure record and exact Git publication below.

### 3. One real capacity attestation

Only after both validation commands pass, record start/end UTC and elapsed seconds and
run exactly once:

```bash
PYTHONDONTWRITEBYTECODE=1 timeout --signal=TERM --kill-after=30s 10m \
  .venv/bin/python \
  scripts/research/attest_binance_usdm_harmonic_capacity.py \
  --store-root data/cex002_qualify \
  --attestation-path \
  research/sprint_004/282_CEX002_GATE2_CAPACITY_ATTESTATION.json
```

Record the exact command, timestamps, elapsed time, exit status, and complete stderr. Do
not retry under any outcome. Exit 0 with either a complete `blocked` or `sufficient`
observation is valid evidence; neither state accepts Gate 2 or authorizes acquisition.
On nonzero or timeout, do not delete, rename, repair, or stage any surviving output path;
record its exact state and identity for reviewer disposition.

### 4. Evidence reconciliation

For an exit-0 attestation, record and reconcile its path, regular-file/no-symlink state,
SHA-256, exact byte length, canonical schema, generated UTC time, receipt/stable basis,
receipt-file/store/output device, attestation source/CLI identity, pre-write/after-staging/
post-publication bytes, stable requirement, current reserve, total requirement, equation,
blockers, state, authorization boundary, and self identity. Recompute the reserve and
total with exact integer arithmetic. Rehash the accepted sizing paths and receipt 258 and
prove they remain unchanged. Do not run another attestation or combine the document with
a later `df` value.

### 5. Record and publication

Write `research/sprint_004/283_CEX002_CAPACITY_ATTESTATION_INTEGRATION_AND_EXECUTION.md`
with every preproof, command, result, reconciliation, failure if any, and exact Git scope.
Make no reviewer decision. Update current task and ticket to require reviewer inspection,
with next ticket `NONE`.

Stage exactly the three accepted source/test paths, record 283, current task, ticket, and
attestation 282 only if the command exited 0 and the document fully reconciles. Run:

```bash
python3 scripts/check_repo_control.py
git diff --cached --check
```

On control success, commit and push only those paths. If validation, Ruff, or attestation
failed, the record and integrated source drop must still be published, but no invalid or
unreconciled attestation may be staged. Stop for reviewer inspection. Do not accept Gate 2
or authorize acquisition even if the attestation says `sufficient`.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly this review, current task, and ticket.
Developer source/test paths, attestation evidence, execution record, and unrelated dirty
work are excluded.
