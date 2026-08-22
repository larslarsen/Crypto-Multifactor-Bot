# CEX-002 Path-Bound Recovery Final Residual Review

**Date:** 2026-08-22
**Reviewer:** Lead Quantitative Finance Researcher/Engineer
**Decision:** `REJECTED_CORRECTION_REQUIRED`
**Gate 1:** Source finding remains accepted; affected publication authority is suspended
**Gate 2:** Not accepted

## Reviewed drop

Claude changed the two paths authorized by review 199:

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `b43aa6006f444dd5529c7765cb80546407d9bd8681c5956ff01b46ff62caed22` |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `9898a4c0c939e74134fbd15279bed9da61c49eeb080f3128b1ae366dd008bf98` |

The test path contains 314 `def test_` functions. The reviewer performed read-only static
inspection only and ran no test, linter, repository-control, acceptance, qualification,
sizing, network, or data-mutation command.

The installed-plan preflight now occurs before persistent recovery and reconciliation,
and the report scenario now uses six months and explicitly proves an outside-plan key
exists. The shared production credit decomposition and all prior exact-singleton and
effective-authority corrections remain accepted. Two fresh-plan/test-fixture residuals
still block integration.

## Findings

### 1. Critical - fresh-plan recovery is absent from its snapshot and accounting

Fresh-plan recovery is deliberately held in `memory_recovered`. `_checkpoint_row()` reads
that mapping, so the recovered keys enter `retained_keys` and the new plan can mark them
`reuse_retained`. But the fresh-plan branch passes `_effective_objects()` to
`BudgetLedger.bootstrap()` and to `retained_evidence_snapshot()`. That view contains only
persisted checkpoint rows and excludes `memory_recovered`.

The result is internally inconsistent: a plan may reuse a valid recovered object while
its frozen retained snapshot records that key with empty digests and zero bytes, and the
bootstrap accounting omits the same retained bytes. After the plan passes, the code
persists those recoveries; the next resume then re-proves real identities against the
empty frozen snapshot and can fail as changed plan inputs.

For a fresh plan, use the combined in-memory evidence view for read-only retained
snapshot and bootstrap/accounting calculations. Persist the exact same proved recovery
set only after the plan passes, so the frozen snapshot, budget state, plan actions, and
eventual checkpoint agree. Add a first-run/rerun test seeded with a basename-unique
retained object and sidecar but no checkpoint or lock: the first plan must reuse it with a
non-empty matching retained snapshot and correct retained accounting, and the immediate
rerun must accept the same inputs without redownload or identity drift.

### 2. High - no-write test searches for an impossible checkpoint row

After the fixture's initial qualification, the sample checkpoint contains objects
acquired or reused through plan entries. `_planned_keys()` includes every entry key.
Therefore the generator that asks for a checkpoint object whose key is not in `planned`
has no valid member and raises `StopIteration` before the preflight assertion.

Construct the valid uncheckpointed recoverable object independently. Add a
candidate-domain family/key with a unique basename that is deterministically outside the
executing plan, retain its object and sidecar bytes without recording it in the sample
checkpoint, and assert those preconditions. Keep the reconcilable reservation and
rejected executing-plan row in the same test, then prove the early refusal performs no
record, flush, settlement, or other durable write and preserves the complete artifact
surface byte-identically.

## Claude correction authority

Sr Dev - Claude Build using Claude Opus 5 is authorized to continue editing only:

- `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py`; and
- `tests/acquisition/test_binance_usdm_harmonic_qualification.py`.

Preserve every correction accepted in reviews 197-200. Make fresh-plan snapshot and
read-only accounting consume the same in-memory recovery evidence that drives
`retained_keys`, add the first-run/rerun identity proof, and construct the no-write test's
valid uncheckpointed recovery independently rather than extracting an impossible row
from the plan-only checkpoint.

Do not weaken lookup, hard-code observed production keys, edit sizing paths, implement a
lineage transition, change repository records, or expand scope. Claude runs no test,
linter, control, qualification, sizing, network, data mutation, Git, commit, or push.
Return both SHA-256 identities and the test-function count, then stop for reviewer
inspection.

## Stop boundary

Hermes remains unauthorized. Gate 2 remains unaccepted. No sizing retry, qualification
execution, authority mutation, bulk acquisition, normalization, catalog publication,
NautilusTrader, Harmonic Trader, payoff, PAPER, LIVE, paid-source, reduced-scope, or
next-ticket work is authorized. Next ticket remains `NONE`.
