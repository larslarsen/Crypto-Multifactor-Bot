# CEX-002 Truncated Test Suite Review

Date: 2026-08-20

Reviewer: Lead Quantitative Finance Researcher/Engineer

Decision: **REJECT TEST DROP; SUPERSEDE REVIEW-84 TEST ACCEPTANCE; RETAIN PRODUCTION
ACCEPTANCE; AUTHORIZE GROK TEST-SUITE RESTORATION**

## Reviewed state

`HEAD == origin/main == eceaa44f3c0f95a3dd03d4a9595bd619ae4945a4`.

Hermes's record 85 is accepted as disciplined execution. It verified the nine hashes,
reported 84/84 focused cases and 11/11 atomic-download cases passing, then stopped at the
authorized Ruff failure before integration or network work. The production module and CLI
reported no Ruff findings. The preserved real store was untouched.

The accepted production module remains:

`src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py`
SHA-256 `7e60ed28d56a32b1722d9c6016ff059c188dfed71481aa5865ca367767d14150`.

## Blocking finding

The 51 `F401` findings are not dead imports to delete. They prove that Spark overwrote the
accumulated uncommitted test source with a correction based on the older committed file.
The reviewed pre-Spark test source was roughly 3,600 lines and contained the review-75
through review-79 sections. The current source ends at 2,039 lines; committed `HEAD` has
only 1,796. The missing sections are exactly the consumers of the 51 now-unused imports.

Deleted coverage includes, at minimum:

- affirmative membership classification for delivery, settlement, TradFi, unresolved,
  funding, and retained official metadata evidence;
- immutable plan validation, input digests, listing/retained authority binding, legacy
  plan preservation, and storage-feasibility reconciliation;
- crash-safe cumulative ledger validation, legacy range, reduced/zero edit rejection,
  rehashed settlement, and explicit transferred/no-transfer dispositions;
- raw exchangeInfo response binding, required identity values, duplicate/incoherent/
  unknown contract semantics, retained snapshots, and stable closed observations;
- full Coinalyze native/provider identity validation and full-universe support gaps;
- volatile-response semantic identity, changed-row plan rejection, rejected-authority
  nonmutation, and original-response recovery; and
- raw-fetch/no-transfer transition proofs introduced by review 79.

Consequently, the 84 passing cases do not represent the accepted focused suite. Review
84's test-source acceptance is superseded. Do not satisfy Ruff by removing the imports;
restore the tests that use them. The production acceptance from reviews 80 and 84 remains
unchanged.

## Restoration contract

Sr Dev - Grok Build using Grok 4.6 High may modify only:

- `tests/acquisition/test_binance_usdm_harmonic_qualification.py`.

Grok must preserve the currently passing core tests and Spark's five corrected contracts,
then reconstruct every deleted review-75 through review-79 test-source section from:

- `research/sprint_004/75_CEX002_GATE1_RESUMABLE_EXECUTION_REVIEW.md` through
  `research/sprint_004/80_CEX002_GROK_TRANSITION_SOURCE_REVIEW.md`;
- `research/sprint_004/82_CEX002_FOCUSED_TEST_FAILURE_REVIEW.md`; and
- `research/sprint_004/83_CEX002_SPARK_TEST_SOURCE_REVIEW.md`.

Every imported production symbol must again support a substantive assertion; no import may
be deleted merely to clear Ruff. Restore focused tests for every category enumerated
above, with no duplicate test names, no production monkeypatch that bypasses the behavior
under test, and no weakening of failure-before-fetch assertions. The oversized fixture
must retain affirmative current membership. The immutable-plan test must retain original
plan facts separately from checkpoint/ledger execution reuse.

Grok authors test source only. It performs no test or lint execution,
production/CLI/fixture/data/repository-record edit, integration, Git operation, commit,
push, network run, purchase, deletion, catalog mutation, Gate 2, Nautilus, or Harmonic
Trader work. It stops for fresh reviewer inspection with the exact test SHA-256 and the
restored test-function count. Hermes and every real rerun remain unauthorized.

## Publication set

Under the narrow reviewer governance exception, the reviewer may stage, commit, and push
exactly:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/86_CEX002_TRUNCATED_TEST_SUITE_REVIEW.md`; and
- `tickets/CEX-002.md`.

No source, test, fixture, data, prior record, or unrelated dirty path belongs to this
publication. The reviewer executes no tests or acceptance commands.

## Disposition

CEX-002 and Gate 1 remain `IN_PROGRESS`. Gate 2, Hermes integration, every real rerun,
Nautilus integration, every other ticket, and Harmonic Trader work remain unauthorized.
Next ticket remains `NONE`.
