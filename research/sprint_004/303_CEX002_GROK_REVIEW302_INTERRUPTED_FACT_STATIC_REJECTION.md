# CEX-002 Grok Review-302 Interrupted-Fact Static Rejection

Date: 2026-08-26
Reviewer: Lead Quantitative Finance Researcher/Engineer
Decision: REJECTED WITHOUT TESTS; exact interrupted-run facts remain
Ticket state: IN_PROGRESS
Next required actor: Sr Dev - Grok Build with xhigh reasoning
Next ticket authorized: NONE

## Inspected return

The reviewer performed one complete static inspection of Grok Build's review-302 return at:

- `src/cryptofactors/acquisition/binance_usdm_harmonic_acquisition.py`:
  `eb4f7b9072b6a4804df2e4a5eeb64d25766b41aa2030b1db07a06f55409a8090`
- `scripts/research/acquire_binance_usdm_harmonic_release.py`:
  `bb6038559d45bddfb011925ad96eb9552cbe4b71bfd5051375adbdcd3de555a9`
  (unchanged)
- `tests/acquisition/test_binance_usdm_harmonic_acquisition.py`:
  `7f58f75e75cdc63c6f3bcd038e93eb6a79639617e709372ecd1a11492dcdf6db`

The files contain 10,461, 151, and 4,627 lines. The test source has 172 test functions.
No developer command result was supplied. The reviewer ran no test or acceptance command.

## Decision

Reject without tests, but preserve and accept the review-302 chain design: predecessor-owned
deltas, original-identity unfinished-run finalization, new-run tail exclusion, retained intent
authentication during head/history walking, exact publication boundaries, and constant-memory
recovery queries are complete static mechanisms. Do not rewrite them.

Only the exact meaning of two interrupted-run facts and one capacity-component comparison remain.

## Complete remaining correction

### 1. Interrupted `error_count` and capacity state are not the accepted run facts

Normal finalization writes `RunCounters.errors`, which counts worker-level terminal/capacity/
budget/fatal failures. `_finalize_interrupted_run()` instead calls `_error_count_between()`,
which counts every non-OK network attempt. These are different domains. A transient 500 followed
by success contributes zero normal run errors but one recovered error; an exhausted four-attempt
request contributes one normal worker error but four recovered errors; a capacity failure may
contribute one normal error and zero recovered errors. The receipt changes meaning solely because
the process was lost.

Interrupted recovery similarly derives `capacity_blocked` only from capacity measured at recovery.
It loses a capacity boundary already crossed by the interrupted invocation when free space later
changes. Measuring post-capacity at the recovery end time is valid; erasing the durable fact that
the run encountered the guard is not.

Persist the exact run-level error count and capacity-blocked event through the coordinator-owned
state as they occur, or replace both normal and interrupted construction with one equivalent
deterministic durable definition. The meaning must be identical on graceful completion and
process-loss recovery, bounded, redacted, race-free, prefix-authenticated, and owned by the same
run identity. Do not infer worker errors from retry-attempt classifications.

Add direct process-loss regressions after a transient retry that later succeeds, after an
exhausted request, and after a capacity stop. Compare the recovered receipt to the accepted
normal semantic definition and prove exact count/block state, predecessor deltas, and chain
verification.

### 2. Stable component values are not exact

`_parse_capacity_fact()` enforces the component key set and total sum but does not compare each
production component to the accepted `STABLE_COMPONENTS` value. Offsetting mutations to two
components keep the same total and pass. The new value test writes a nonexistent
`stable_requirement_bytes` component, so it exercises only the extra-key check.

Require the complete component mapping to equal the applicable accepted mapping exactly. Correct
the value regression to mutate a real component while preserving the total through an offsetting
second-component mutation; it must fail on the component-value proof rather than key-set or total.
Keep the non-production one-component authority case exact as well.

## Grok correction authorization

Keep Grok at xhigh for this concurrency/run-semantic correction. Grok Build may edit only:

- `src/cryptofactors/acquisition/binance_usdm_harmonic_acquisition.py`
- `scripts/research/acquire_binance_usdm_harmonic_release.py`
- `tests/acquisition/test_binance_usdm_harmonic_acquisition.py`

Preserve all accepted review-302 mechanisms and every earlier accepted authority, economic,
capacity, filesystem, attempt, charge, retained, terminal, and boundedness contract. Implement
both groups and their direct tests together. Do not use Git, edit repository records, or execute
tests or other commands. Hermes owns test execution and developer-source integration after static
acceptance.

Stop once with exact three-path scope, final SHA-256 values, line and test-function counts, and
confirmation that no command ran. No real plan, network, data, Gate 3, normalization, catalog,
NautilusTrader, Harmonic Trader, PAPER/LIVE, or next-ticket work is authorized.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly this record,
`docs/handoff/CURRENT_TASK.md`, and `tickets/CEX-002.md`. Developer source/test paths,
state/data/evidence, and unrelated dirty work are excluded.
