# CEX-002 Claude Targeted Test Failure and Correction

Date: 2026-08-24
Reviewer: Lead Quantitative Finance Researcher/Engineer
Decision: REJECTED ON TARGETED TEST; one correction continuation authorized
Ticket state: IN_PROGRESS
Next required actor: Sr Dev - Claude Build on Claude Opus 5
Next ticket authorized: NONE

## Inspected drop and execution

The reviewer inspected Claude Build's review-289 drop at these identities:

- `src/cryptofactors/acquisition/binance_usdm_harmonic_acquisition.py`:
  `2540d0eca45e28f699bdbc55a3f1f268ac1dfe22e0a4fd2a715331386e17240d`
- `scripts/research/acquire_binance_usdm_harmonic_release.py`:
  `bb6038559d45bddfb011925ad96eb9552cbe4b71bfd5051375adbdcd3de555a9`
- `tests/acquisition/test_binance_usdm_harmonic_acquisition.py`:
  `8878c2914141e8ca192748ace2c8122cdedf817edce63626ec9950095de70634`

All three paths parse. The test source contains 74 test functions. Claude correctly ran
the one authorized command once and stopped without repair or rerun:

```text
49 failed, 25 passed
exit status 1
```

Forty-six failures share `UnsafeStateError: an unexpected worker failure stopped the
run`, raised after an exception outside the typed worker sets. The run also reports the
exclusive-lock failure and its `BlockingIOError` cause, one fixture `FileExistsError`,
and one CLI `assert 6 == 3` downstream of the worker fatal. No correction, second test,
Ruff, Git, real data, or network command ran.

## Decision

Reject the drop for integration. This is one failed corrective drop, not 49 independent
reviews. The broad failure is a shared production-path defect masked by the generic
worker boundary. Two additional failures are invalid test setups. The review-289 rewrite
and its 74-test regression inventory remain the correction base; do not discard or split
them.

Claude Build retains the assignment because this is its first correction result on this
bounded drop and it still has the complete implementation context. This review supersedes
review 289's stop-after-test state and authorizes exactly one correction continuation.

## Required correction

1. Find and correct the first underlying exception outside the typed worker sets on the
   ordinary synthetic acquisition path. Do not make the suite pass by swallowing the
   exception, returning partial success, reclassifying every Python exception as an
   ordinary object error, or weakening assertions. The worker boundary must preserve a
   bounded, secret-safe diagnostic type/cause, stop scheduling, settle every worker and
   coordinator, and propagate an unsafe-state fatal distinctly. Expected provider,
   authority, capacity, budget, injected-fault, and retry failures must retain their
   designed classes and exits.

2. Correct `test_fresh_plan_installs_two_hundred_two_unsupported_gaps`: it currently
   opens the exclusive state lock and calls replaying `run_plan()` before closing that
   state. Inspect the first state, close it, then replay and prove the same plan identity
   and exact 202 gaps. Do not weaken exclusive-lock production behavior.

3. Correct `test_retained_tamper_is_fail_closed`: its `universe` fixture already creates
   the same `tmp_path` tree before the test calls `build_universe(tmp_path, ...)`, causing
   the fixture `mkdir()` failure. Use one independently built universe and preserve the
   retained-tamper fail-closed assertion. Do not add `exist_ok=True` in a way that merges
   unrelated fixture authority trees.

4. Make `AcquisitionState.open()` release every descriptor and any acquired lock on all
   failure paths, including lock contention, SQLite connection/setup, integrity, schema,
   and domain authentication. `bind_session()` must not leak a writer lock when opening
   fails. Preserve the exact no-follow and one-writer rules.

5. Reconcile the downstream CLI expected exit only by fixing the shared production
   failure. Preserve the expected complete-with-typed-gaps result for a valid synthetic
   universe and the distinct authority/unsafe/capacity/partial exits.

6. Preserve all review-288 and review-289 architecture, authority, budget, provider-
   semantic, reconciliation, bounded-memory, no-follow/no-replace, retry, closure, and
   regression requirements. Retain all valid tests; do not delete, skip, xfail, loosen,
   duplicate, or replace production-path tests with mocks of the result being proved.

## Exact scope and one rerun

Claude Build may edit exactly:

1. `src/cryptofactors/acquisition/binance_usdm_harmonic_acquisition.py`
2. `scripts/research/acquire_binance_usdm_harmonic_release.py`
3. `tests/acquisition/test_binance_usdm_harmonic_acquisition.py`

Do not edit or disturb any other path. Use no Git. After the complete correction is
written, run exactly once:

```bash
PYTHONDONTWRITEBYTECODE=1 timeout --signal=TERM --kill-after=30s 10m \
  .venv/bin/python -m pytest \
  tests/acquisition/test_binance_usdm_harmonic_acquisition.py -q --tb=short
```

On nonzero result or timeout, stop without repair or rerun. Run no other test, Ruff,
control, qualification, sizing, capacity, plan, acquisition, verification, network, or
Git command. Stop once with all three SHA-256 hashes, test-function count, exact command
output/status, the first underlying worker exception type corrected, and confirmation
that only the three authorized paths changed.

Hermes integration, acceptance commands, real planning/network/data/state/evidence, Git,
commit/push, Gate-2 acceptance, Gate 3, normalization, catalog, NautilusTrader, Harmonic
Trader, PAPER/LIVE, and next-ticket work remain unauthorized.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly this review, current task, and ticket.
Developer source/test paths, data/state/evidence, and unrelated dirty work are excluded.
