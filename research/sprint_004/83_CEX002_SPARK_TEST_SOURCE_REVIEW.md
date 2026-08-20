# CEX-002 Spark Test Source Review

Date: 2026-08-20

Reviewer: Lead Quantitative Finance Researcher/Engineer

Decision: **REJECT TEST DROP; ACCEPT THREE CLOSURES; AUTHORIZE ONE FINAL TEST-ONLY
SPARK CORRECTION**

## Reviewed state

Committed control-plane base:
`HEAD == origin/main == 8f8ea888d32b50148bec68997454338c396b9770`.

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `7e60ed28d56a32b1722d9c6016ff059c188dfed71481aa5865ca367767d14150` |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `79dfbebd34a2fb24139c912409a8db58d598771396980e5e1da328d502bb3289` |

The accepted production module, CLI, and all seven fixtures remain unchanged. Spark
changed only the test path authorized by review 82. Every unrelated dirty path remains
excluded. The reviewer performed static inspection only and ran no tests or acceptance
commands.

## Accepted closures

Three review-82 corrections are exact:

1. The authenticated current contract with no kline prefix now expects the precise
   blocking `current_unarchived` gap.
2. The complete bookTicker/bookDepth fixture now preserves official authority and
   nonblocked release while expecting `qualified_with_typed_gaps`, `typed_gaps`, and the
   nonblocking family-launch head gap.
3. The incomplete exchangeInfo-row test now supplies a valid positive `serverTime`, so it
   isolates missing row identity fields rather than failing on its envelope.

Those corrections and every review-79 test must be preserved.

## Residual findings

### 1. Oversized-source coverage still lacks affirmative membership

The oversized-object fixture now supplies both trades and aggregate-trades groups and
contiguous months, but its `run_source_qualification` call still omits
`current_contracts`. Review 82 explicitly required affirmative current-perpetual
membership so the test isolates the sample budget from membership blocking. Pass
`_contracts("BTCUSDT")` to that run and retain the no-raw-fetch, complete inventory, typed
budget-block, and non-inaccessible assertions.

### 2. The original immutable-plan failure assertions remain

The retained-object test correctly compares plan version, digest, entries, and key counts
across runs and separately checks no raw/checksum refetch plus unchanged ledger charges.
It then contradicts those comparisons by retaining the three stale assertions that the
locked plan has one retained object, positive retained bytes, and zero new-download bytes.
The first plan selected a download, so both reports must retain one unique new object,
zero unique retained objects, zero retained bytes, and the original positive planned
download bytes. Remove the stale expectations and assert those immutable first-plan facts
instead. Execution reuse and the unchanged single transferred ledger charge remain the
separate resume proof.

## Bounded correction authorization

Implementation Dev - Codex Spark using GPT-5.3-Codex-Spark High may modify only:

- `tests/acquisition/test_binance_usdm_harmonic_qualification.py`.

It must make only the two corrections above and preserve all accepted test work. Spark
authors test source only. It performs no test execution, production/CLI/fixture/data or
repository-record edit, integration, Git operation, commit, push, network run, purchase,
deletion, catalog mutation, Gate 2, Nautilus, or Harmonic Trader work. It stops for fresh
reviewer inspection with the exact test SHA-256. Hermes and every real rerun remain
unauthorized.

## Publication set

Under the narrow reviewer governance exception, the reviewer may stage, commit, and push
exactly:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/83_CEX002_SPARK_TEST_SOURCE_REVIEW.md`; and
- `tickets/CEX-002.md`.

No source, test, fixture, data, prior record, or unrelated dirty path belongs to this
publication. The reviewer executes no tests or acceptance commands.

## Disposition

CEX-002 and Gate 1 remain `IN_PROGRESS`. Gate 2, Hermes integration, every real rerun,
Nautilus integration, every other ticket, and Harmonic Trader work remain unauthorized.
Next ticket remains `NONE`.
