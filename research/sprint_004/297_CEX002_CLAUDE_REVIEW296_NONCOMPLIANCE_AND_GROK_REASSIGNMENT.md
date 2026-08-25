# CEX-002 Claude Review-296 Noncompliance and Grok Reassignment

Date: 2026-08-25
Reviewer: Lead Quantitative Finance Researcher/Engineer
Decision: REJECTED WITHOUT TESTS; Claude deauthorized and review 296 reassigned
Ticket state: IN_PROGRESS
Next required actor: Sr Dev - Grok Build on Grok 4.6 High
Next ticket authorized: NONE

## Inspected return

The reviewer performed one complete static inspection of Claude Build's claimed review-296
correction at:

- `src/cryptofactors/acquisition/binance_usdm_harmonic_acquisition.py`:
  `70189c3011a1e3bcd5c36043bc76aa46bd26cb273414cc082d6d475edbf7cdf9`
- `scripts/research/acquire_binance_usdm_harmonic_release.py`:
  `bb6038559d45bddfb011925ad96eb9552cbe4b71bfd5051375adbdcd3de555a9`
  (unchanged)
- `tests/acquisition/test_binance_usdm_harmonic_acquisition.py`:
  `d7a29a870b3d90a18f35807238a9a3c1e288a1adef5ae4661364a5d64532a52b`

The files contain 8,275, 151, and 3,356 lines. The test source has 124 test functions.
No developer command result was supplied. The reviewer ran no test or acceptance command
because the correction remains materially incomplete on static inspection.

## Decision

Reject the return as noncompliant with review 296. It adds only 47 source lines and two
tests to the snapshot rejected there. Preserve the useful additions: historical seal links
are compared with their receipt predecessor, prefix, and marks; terminal receipts expose a
chain summary; and the two local chain mutations improve coverage.

Those fragments do not complete any of review 296's seven correction groups:

1. `load_authority_bundle()` still omits `roots` when calling helper/code, attestation,
   holdout, cost, and Coinalyze authority operations. Pathname prechecks remain, and
   `open_dir_chain()`/`open_parent_dir()` still deliberately open a new pathname root for
   an out-of-capability path.
2. `AcquisitionState.open()` still pre-proves only `-wal` and `-shm`, not the rollback
   `-journal` leaf SQLite may inspect before WAL mode is established. `run_acquire()` and
   `verify_state()` still perform post-bind partial cleanup before their session-closing
   `try/finally` blocks.
3. Run receipts still omit `run_id`; `_validate_receipt_document()` still checks only four
   generic fields; historical receipt validation remains inexact; and a finished run with
   a published receipt but no `run_seal` row is still rejected instead of recovered.
4. Charge recovery still lacks one exact descriptor/plan/completion validator, and terminal
   verification still accepts a query substring in the retrieval URL. The new batch helper
   selects every charge-generation row but resolves each to the latest identity generation,
   so a released-then-retried identity can materialize the same newest generation more than
   once in one recovery pass.
5. A transport-raised `AcquisitionError` is still recorded as terminal with a null status,
   contradicting the authenticated attempt domain. The direct transport/read/validator/
   close/exhaustion and remaining cross-row domain regressions are absent.
6. Initial retained decomposition and proof remain pathname-based, exact source device and
   sidecar facts remain incomplete, and the extra-inventory test still corrupts the old
   content-addressed path instead of isolating mapping equality.
7. The terminal manifest still emits neither the authority record nor an explicit paired
   ledger fact, so it cannot independently reconstruct the authenticated prefix. The large
   run test remains a GC-container heuristic rather than deterministic production-path
   bound instrumentation.

Review 296 remains the complete correction contract. This review adds no replacement
architecture, no new economic requirement, and no second implementation checklist.

Claude has now returned two partial corrections against the same complete contract. Under
the repository's repeated-miss routing rule, continuing with Claude is not an efficient use
of senior or reviewer usage. Review 297 supersedes review 295's actor deauthorization only:
Grok Build is reauthorized for one complete implementation of review 296 against the frozen
snapshot above.

## Grok correction authorization

Grok Build may edit only:

1. `src/cryptofactors/acquisition/binance_usdm_harmonic_acquisition.py`
2. `scripts/research/acquire_binance_usdm_harmonic_release.py`
3. `tests/acquisition/test_binance_usdm_harmonic_acquisition.py`

Implement review 296 literally and completely as one source-and-regression return. Preserve
accepted authority, economic scope, counts, bytes, capacity, ADR-0029 layer boundaries, and
the useful corrections already present. Do not edit any other path and use no Git.

No test may run until all seven review-296 source groups and their direct regressions are
present. The targeted allowance does not reset: across reviews 295-297, at most three runs
of the exact review-291 pytest command are permitted, counting any unreported run. Grok may
make contract-bounded repairs between those runs. Run no Ruff, control, qualification,
sizing, capacity, real plan/acquire/verify, network, Git, or other command.

Stop once with final hashes, line and test-function counts, the exact three-path scope,
every authorized command and result including cumulative run number, and the original
exception type/cause for any failure. Hermes retains integration, broader tests and
acceptance commands, evidence, and developer-source Git. No real plan, data, Gate 3,
normalization, catalog, NautilusTrader, Harmonic Trader, PAPER/LIVE, or next-ticket work is
authorized.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly this review,
`docs/handoff/CURRENT_TASK.md`, and `tickets/CEX-002.md`. Developer source/test paths,
state/data/evidence, and unrelated dirty work are excluded.
