# CEX-002 Grok Review-299 Chain-Delta Static Rejection

Date: 2026-08-26
Reviewer: Lead Quantitative Finance Researcher/Engineer
Decision: REJECTED WITHOUT TESTS; one architecture-sensitive chain correction remains
Ticket state: IN_PROGRESS
Next required actor: Sr Dev - Grok Build with xhigh reasoning
Next ticket authorized: NONE

## Inspected return

The reviewer performed one complete static inspection of Grok Build's review-299/301 return at:

- `src/cryptofactors/acquisition/binance_usdm_harmonic_acquisition.py`:
  `d4d79eeb9abb56fb97bb5f3c45bd226fe3b7359b4cf13ad91545213cb31f7eea`
- `scripts/research/acquire_binance_usdm_harmonic_release.py`:
  `bb6038559d45bddfb011925ad96eb9552cbe4b71bfd5051375adbdcd3de555a9`
  (unchanged)
- `tests/acquisition/test_binance_usdm_harmonic_acquisition.py`:
  `2f80e3b31854b9c1f656044b904dc99002174aea2fc22c452153fbda1f7667fb`

The files contain 10,132, 151, and 4,441 lines. The test source has 162 test functions.
No developer command result was supplied. The reviewer ran no test or acceptance command.

## Decision

Reject without tests, but preserve the return. It removes the parallel old/new finalization
path and implements one transactional `run_publication` intent, exact receipt/locator/seal/head
publication boundaries, configured-root recovery, exact top-level receipt types and fields,
historical semantic calculation, authenticated run facts in the prefix, and the requested
receipt mutation, crash-prefix, and direct attempt-failure regressions. Those mechanisms are
accepted and must not be rewritten.

One architecture-sensitive chain invariant remains, plus two consequences of the same durable
intent design. This is the complete remaining static correction.

## Complete remaining correction

### 1. Receipt deltas must start at the sealed predecessor, not an invocation snapshot

`finish_run()` and `_validate_run_receipt_facts()` derive attempt, completion, gap, and byte
deltas from `run_metadata.start_snapshot`. They never require that snapshot's watermarks equal
the receipt predecessor's sealed watermarks. Under the graceful test path they happen to match.
After a real process loss before `finish_run()`, however, `run_metadata` remains unfinished and
attempt/completion facts may remain beyond the head. `_recover_published_receipt_head()` ignores
that unfinished run. The next invocation snapshots those abandoned tail facts, reports zero
deltas for them, and then seals them in its prefix. The chain can therefore authenticate facts
which no receipt delta or finished run owns.

Make the chain invariant literal: every run receipt's deltas are the exact difference between
its predecessor seal/plan watermarks and its current watermarks. A new run must never begin over
an unfinished run or unsealed fact tail. Recover/finalize the interrupted run under its own
identity, or durably continue that exact run, with enough bounded durable run facts to construct
one truthful canonical receipt after process loss. Do not delete, relabel, double count, or let a
later invocation absorb the abandoned facts.

Validate the start snapshot against the exact predecessor marks and validate every delta from
predecessor to current marks during initial finalization, recovery, head authentication, and
historical chain walking. Add process-loss regressions after run creation and after durable
attempt/completion progress but before finalization. Resume must produce exact ownership,
predecessor/current deltas, network-call counts, and a terminating authenticated chain.

### 2. Give publication intent an exact authenticated lifecycle

`run_publication` is required to exist for every finished run, including fully sealed history,
but completed-head authentication does not validate its digest, directory, or body. The new
malformed/conflicting intent tests reset the head to force recovery; the same mutations are
otherwise accepted on a completed chain. This leaves required mutable state outside both the
immutable receipt proof and authenticated prefix.

Define one lifecycle and enforce it exactly. Either stream and compare every retained intent to
its immutable receipt/run/seal facts during normal head and historical authentication, or remove
an intent only after its head is durably complete and make its absence the exact authenticated
completed state. A completed chain must not require an unvalidated row. Add direct completed-head
mutation/deletion tests without manually rewinding valid state.

The nested `stable_components` capacity object also accepts any string key set and does not
validate the accepted capacity equations. Require the exact component key set for the applicable
authority and validate the stable requirement, reserve, total, needed, transfer, reserve floor,
and sufficient/blocked equation at finalization and replay. Add independent nested extra,
missing, value, and equation regressions.

### 3. Keep recovery memory bounded across run history

`_recover_published_receipt_head()` materializes every finished run with `fetchall()` and builds
an unbounded Python list of unpublished identities. Run history grows on every resume, so this
violates the accepted bounded production contract even though receipt-directory enumeration was
removed. Use streaming cursor batches or exact indexed `LIMIT 2` ambiguity queries and retain at
most constant/batch memory. Add a many-run regression which observes the bound, not merely the
final result.

## Grok correction authorization

This correction requires xhigh reasoning because interrupted-run ownership changes the receipt
chain state machine. Grok Build may edit only:

- `src/cryptofactors/acquisition/binance_usdm_harmonic_acquisition.py`
- `scripts/research/acquire_binance_usdm_harmonic_release.py`
- `tests/acquisition/test_binance_usdm_harmonic_acquisition.py`

Preserve the accepted review-299 publisher, exact fault boundaries, field validators, attempt
correction, manifest/configured roots, charge logic, retained proof, terminal reconstruction,
authority, economic scope, counts, bytes, capacity, and bounded collections. Implement all three
groups and their direct tests together. Do not use Git, edit repository records, or execute tests
or other commands. Hermes owns test execution and developer-source integration only after static
acceptance.

Stop once with exact three-path scope, final SHA-256 values, line and test-function counts, and
confirmation that no command ran. No real plan, network, data, Gate 3, normalization, catalog,
NautilusTrader, Harmonic Trader, PAPER/LIVE, or next-ticket work is authorized.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly this record,
`docs/handoff/CURRENT_TASK.md`, and `tickets/CEX-002.md`. Developer source/test paths,
state/data/evidence, and unrelated dirty work are excluded.
