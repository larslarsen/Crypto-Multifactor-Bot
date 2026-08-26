# CEX-002 Grok Review-298 Receipt Static Rejection

Date: 2026-08-26
Reviewer: Lead Quantitative Finance Researcher/Engineer
Decision: REJECTED WITHOUT TESTS; one receipt-bound correction remains with Grok Build
Ticket state: IN_PROGRESS
Next required actor: Sr Dev - Grok Build on Grok 4.6 High
Next ticket authorized: NONE

## Inspected return

The reviewer performed one complete static inspection of Grok Build's review-298 return at:

- `src/cryptofactors/acquisition/binance_usdm_harmonic_acquisition.py`:
  `fc636eb4cc7b5ee41350f0058b89d205e4dbdcadeb792ff4031c82f0eeb32f5a`
- `scripts/research/acquire_binance_usdm_harmonic_release.py`:
  `bb6038559d45bddfb011925ad96eb9552cbe4b71bfd5051375adbdcd3de555a9`
  (unchanged)
- `tests/acquisition/test_binance_usdm_harmonic_acquisition.py`:
  `0cbf58604525c0b6f26bc9d4adff9354fe95565dcbcc4462142e80f07f765f10`

The files contain 9,682, 151, and 3,937 lines. The test source has 151 test functions.
No developer command result was supplied. The reviewer ran no test or acceptance command.

## Decision

Reject the return without tests, but retain Grok for one narrowly bounded receipt correction.
Review 298 groups 1, 3, 4, and 5 are accepted: the acquisition-owned manifest stream and
configured receipt roots, attempt/charge source correction, unconditional retained proof,
and terminal digest reconstruction are no longer open source-design findings. Do not rewrite
those mechanisms. Only the exact direct attempt regressions named below remain from those
groups.

The run-receipt subsystem is still not crash recoverable or an exact authenticated record.
This is the complete remaining static correction; do not return another partial subset.

## Complete remaining correction

### 1. Make finalized run intent durable before any receipt publication

`finish_run()` durably marks a run finished before any durable receipt intent exists.
`run_acquire()` then publishes the content-named receipt and creates the per-run locator as
two separate filesystem operations. `_recover_published_receipt_head()` can find an orphaned
finished run only through that locator. A process loss after `finish_run()` but before receipt
publication, or after receipt publication but before locator publication, therefore leaves a
finished run which recovery permanently rejects as having no published receipt. The existing
`after_run_receipt_publication` fault is after both writes and cannot exercise either crash
state.

Persist one exact canonical run-receipt intent, including its content identity and accepted
directory, atomically with run finalization before external publication. Recovery must validate
the intent against durable state and predecessor watermarks, publish or re-prove the exact
receipt, create or re-prove its exact locator, insert or re-prove the seal, and CAS or re-prove
the head. Do not enumerate receipt directories or accept an arbitrary candidate. Every prefix
of this state machine, including no receipt, receipt without locator, locator without seal,
seal without head, and completed head, must resume deterministically and idempotently.

Put real fault points immediately before and after receipt publication, locator publication,
seal insertion, and head CAS. Names must describe the actual boundary. Test every prefix,
including the configured receipt-root override and malformed, missing, conflicting, and
ambiguous exact identities. A fault after the final head CAS must also replay cleanly.

### 2. Authenticate every run-receipt field exactly

`_run_receipt_facts()` currently coerces untrusted JSON values with `int()`, `list()`,
`dict()`, and `bool()` instead of requiring exact JSON types and bounded shapes.
`_validate_run_receipt_facts()` derives only attempt/completion/byte deltas, open charges,
and two count fields. `gap_delta`, `error_count`, `network_sample`, both capacity snapshots,
`capacity_blocked`, most of `counts`, and their bounds remain self-asserted. Copying the same
receipt values into `run_seal.facts_json` and comparing them back is not independent proof of
their truth.

Persist or deterministically derive every retained field as part of the durable intent and
compare every field exactly during initial sealing, recovery, head authentication, and
historical chain walking. Require exact integer/string/list/object/boolean types, exact key
sets, finite bounds, sample order and ceilings, and no coercion. Derive deltas and counts at
the receipt's exact predecessor/current watermarks, including gaps and the sealed Coinalyze
ledger equation. Bind the durable intent/facts into authenticated state; do not leave mutable
facts outside both the immutable receipt identity and the authenticated prefix.

`semantic_state_digest` must always equal the one historical semantic digest derived from
that receipt's prefix and ledger at its own charge/transition watermarks. Do not skip this on
recovery/history and do not accept a choice of current-live or historical values.

Add independent mutation/type/boundary regressions for every run-receipt field. Each test must
isolate its named field and fail for the intended exact validation, not merely because a whole
receipt or unrelated prefix was made non-canonical.

### 3. Close the already-required direct attempt regression matrix

The corrected attempt source is accepted, and the new close regression is useful. Add direct
one-call regressions for transport/header acquisition failure, streamed read failure,
provider-validator failure, injected interruption, and close failure. Each must prove exactly
one durable attempt for the original bounded cause, its exact class/status domain, bounded
redacted diagnostic, private-file cleanup where applicable, and successful state-domain
authentication before a receipt can seal it. Do not redesign the accepted attempt path.

## Grok correction authorization

Grok Build may edit only:

- `src/cryptofactors/acquisition/binance_usdm_harmonic_acquisition.py`
- `scripts/research/acquire_binance_usdm_harmonic_release.py`
- `tests/acquisition/test_binance_usdm_harmonic_acquisition.py`

Preserve the four accepted review-298 source groups and all authority, economic scope, counts,
bytes, capacity, and boundedness contracts. Implement the entire correction and direct tests
together. Do not use Git and do not edit repository records or any other path. Under the current
development-role contract Grok does not execute tests; Hermes owns targeted and acceptance test
execution after static source acceptance.

Stop once with exact three-path scope, final SHA-256 values, line and test-function counts, and
confirmation that no command was run. No real plan, network, data, Gate 3, normalization,
catalog, NautilusTrader, Harmonic Trader, PAPER/LIVE, or next-ticket work is authorized.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly this review,
`docs/handoff/CURRENT_TASK.md`, and `tickets/CEX-002.md`. Developer source/test paths,
state/data/evidence, and unrelated dirty work are excluded.
