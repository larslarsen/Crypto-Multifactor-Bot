# CEX-002 Grok Review-305 Test Assertion Residual

Date: 2026-08-26
Reviewer: Lead Quantitative Finance Researcher/Engineer
Decision: REJECTED WITHOUT TESTS; FIVE TESTS HAVE MECHANICAL ASSERTION RESIDUALS
Ticket state: IN_PROGRESS
Next required actor: Implementation Dev - Codex Spark
Next ticket authorized: NONE

## Inspected return

The reviewer performed one complete static inspection of Grok Build's review-305 return at:

- `src/cryptofactors/acquisition/binance_usdm_harmonic_acquisition.py`:
  `9476ccff836542509efe7e5169f0cb9d10d40a831fde0153415a4a667ff97065`
- `tests/acquisition/test_binance_usdm_harmonic_acquisition.py`:
  `9f138be658cf2ab9042f43c0e2f8ae783ac6fbe8df985bf129f8fc8d34bcb995`
- `scripts/research/acquire_binance_usdm_harmonic_release.py`:
  `bb6038559d45bddfb011925ad96eb9552cbe4b71bfd5051375adbdcd3de555a9`
  (unchanged)

The source and test files contain 10,522 and 4,895 lines. The test source has 177 test
functions. No developer command result was supplied. The reviewer ran no test or acceptance
command.

## Static disposition

The production source correction is accepted and must not be changed. It translates a retained
raw no-follow open failure into an explicit retained-source authority error while preserving the
cause, and makes both predecessor-watermark diagnostics precise.

The corrected unfinished-run helper uses the production bound session and `begin_run()` path and
closes the session without finalizing it. The three charge fixtures now leave facts owned by that
run; the new orphan-tail regression preserves fail-closed behavior. The two publication fixtures
now use the exact `before_run_seal_insert` and `before_run_receipt_publication` fault boundaries.
The interrupt wrapper now iterates `response.iter_bytes` rather than calling it. These mechanisms
satisfy review 305.

Five tests contain assertions which are mechanically wrong or weaker than the fixture proves.

### 1. Recovered receipt becomes the next run's predecessor

Both corrected publication tests call `_acquire()` to resume. Session binding first recovers and
seals the interrupted publication, but that same invocation then begins, finishes, and publishes
a new run. Therefore the final `seal_head.receipt_sha256` is the returned resumed run receipt,
not the recovered receipt. The recovered receipt is the new head's exact predecessor.

In both `test_published_receipt_without_seal_is_recovered` and
`test_missing_filesystem_receipt_is_republished_from_intent`:

- select both `receipt_sha256` and `predecessor_sha256` from `seal_head`;
- retain the assertion that the recovered receipt has a `run_seal` row;
- require the final head receipt to equal `resumed["run_receipt"]["sha256"]`; and
- require the final head predecessor to equal the recovered `receipt_sha`.

Do not assert that the final head receipt itself equals the recovered receipt, remove the resumed
run, or change production recovery.

### 2. Fixture-owned watermarks are exact

The three unfinished-run fixtures start from the plan head, so their first interrupted receipt
has exact charge and transition high-watermarks:

- `test_crash_before_publication_refunds_the_reservation`: `charge_hi == 1` and
  `transition_hi == 1`;
- `test_a_released_charge_is_retried_as_a_new_generation`: `charge_hi == 1` and
  `transition_hi == 1`; and
- `test_valid_released_then_retried_generation_is_handled_once`: `charge_hi == 1` and
  `transition_hi == 2`.

Replace the six `>=` assertions with these exact equalities. Do not otherwise edit the fixtures.

## Spark correction authorization

This is a bounded mechanical test-source correction. Spark may edit only:

- `tests/acquisition/test_binance_usdm_harmonic_acquisition.py`

Preserve every other Grok change byte-for-byte. Do not edit production source, the CLI, control
documents, or unrelated work. Do not use Git or run tests or other commands. Stop once with the
test-file SHA-256, line count, test-function count, and confirmation that no command ran. Hermes
owns integration and test execution only after reviewer static acceptance.

Real plan/acquire/verify, network, data, Ruff, full suite, control, evidence edits, Gate 3,
normalization, catalog, NautilusTrader, Harmonic Trader, PAPER/LIVE, and next-ticket work remain
unauthorized.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly this record, `docs/handoff/CURRENT_TASK.md`, and
`tickets/CEX-002.md`. Developer source/test paths, state/data/evidence, and unrelated dirty work
are excluded.
