# CEX-002 Grok Token Exhaustion and Claude Continuation

Date: 2026-08-26
Reviewer: Lead Quantitative Finance Researcher/Engineer
Decision: PRESERVE PARTIAL SOURCE; reassign the incomplete review-299 correction to Claude Build
Ticket state: IN_PROGRESS
Next required actor: Sr Dev - Claude Build on Claude Opus 5
Next ticket authorized: NONE

## Preserved partial snapshot

Grok Build exhausted its context before completing review 299. The reviewer inspected the
result only far enough to determine continuation safety. This is not a completed return, an
acceptance review, or authorization to test.

- `src/cryptofactors/acquisition/binance_usdm_harmonic_acquisition.py`:
  `70e823e01badb99921acd4214cff8d5f4f748aabc2ea10db80c0e6bbe79b4c94`
  (10,074 lines)
- `scripts/research/acquire_binance_usdm_harmonic_release.py`:
  `bb6038559d45bddfb011925ad96eb9552cbe4b71bfd5051375adbdcd3de555a9`
  (unchanged, 151 lines)
- `tests/acquisition/test_binance_usdm_harmonic_acquisition.py`:
  `0cbf58604525c0b6f26bc9d4adff9354fe95565dcbcc4462142e80f07f765f10`
  (unchanged, 3,937 lines and 151 test functions)

No developer command result was supplied. The reviewer ran no test or acceptance command.

## Continuation assessment

Preserve the partial source. It contains useful foundations: expanded durable run metadata,
a `run_publication` intent table, exact-watermark helpers, and a transactional `finish_run()`
prototype. It is not internally connected or runnable:

1. `run_seal.facts_json` was removed from the schema, but the ordinary acquisition path still
   inserts that removed column and still calls `_run_receipt_facts()`.
2. The ordinary `finish_run()` call supplies only the old arguments. The new durable fields
   therefore receive zero/empty defaults and an empty authority/code identity, while the caller
   then rebuilds and publishes a second old-style receipt outside the intent.
3. Publication and recovery still follow the old receipt-then-locator path and retain only the
   old after-publication/after-seal/after-head fault names. The exact before/after crash-prefix
   state machine required by review 299 is not wired.
4. The test source is unchanged. The receipt field/type mutation, crash-prefix, configured-root
   recovery, and direct attempt-failure regression matrices remain absent.

## Claude continuation authorization

Review 299 remains the complete engineering contract. Claude Build must finish it from the
preserved snapshot, not start another redesign and not return only the four observations above.
Claude may edit only:

- `src/cryptofactors/acquisition/binance_usdm_harmonic_acquisition.py`
- `scripts/research/acquire_binance_usdm_harmonic_release.py`
- `tests/acquisition/test_binance_usdm_harmonic_acquisition.py`

Complete one canonical path: finalization atomically persists exact validated receipt intent;
publication and every recovery prefix use that intent; receipt, locator, seal, and head are each
published/re-proved idempotently at exact before/after fault boundaries; all receipt fields and
the one historical semantic digest are exactly typed and independently authenticated; and the
complete review-299 direct regression matrix is present.

Preserve the review-299 acceptance of manifest/configured-root source, attempt/charge source,
retained proof, and terminal reconstruction. Remove superseded partial code rather than keeping
parallel old/new finalization paths. Do not change authority, economic scope, counts, bytes,
capacity, or boundedness. Do not use Git, edit repository records, or run tests or any other
command. Hermes owns test execution and developer-source integration after reviewer static
acceptance.

Stop once with exact three-path scope, final SHA-256 values, line and test-function counts, and
confirmation that no command ran. No real plan, network, data, Gate 3, normalization, catalog,
NautilusTrader, Harmonic Trader, PAPER/LIVE, or next-ticket work is authorized.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly this record,
`docs/handoff/CURRENT_TASK.md`, and `tickets/CEX-002.md`. Developer source/test paths,
state/data/evidence, and unrelated dirty work are excluded.
