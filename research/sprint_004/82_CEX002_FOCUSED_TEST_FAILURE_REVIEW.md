# CEX-002 Focused Test Failure Review

Date: 2026-08-20

Reviewer: Lead Quantitative Finance Researcher/Engineer

Decision: **ACCEPT HERMES STOP; RETAIN PRODUCTION ACCEPTANCE; AUTHORIZE ONE TEST-ONLY
SPARK CORRECTION**

## Reviewed state

`HEAD == origin/main == 2b5fa8855c420024c793cafa1f97f970addcc531`.

Hermes verified all nine review-80 hashes, ran the first authorized command, recorded five
focused-suite failures in
`research/sprint_004/81_CEX002_GATE1_STABLE_AUTHORITY_EXECUTION.md`, published only the
three authorized evidence/control paths, and stopped. It did not run commands 2 through
5, stage or commit the accepted source drop, load the API key, touch the preserved real
store, or perform a network qualification. That execution discipline is accepted.

The accepted production module remains exactly:

`src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py`
SHA-256 `7e60ed28d56a32b1722d9c6016ff059c188dfed71481aa5865ca367767d14150`.

Static inspection classifies all five failures as stale or internally inconsistent test
contracts. No production correction is authorized.

## Failure dispositions

### 1. Current-unarchived precedence is correct

`test_absent_family_prefix_blocks_official_complete` authenticates ETHUSDT as a current
perpetual and then supplies no ETHUSDT kline prefix. The implemented status
`current_unarchived` is the more precise required gap from reviews 75/76; expecting the
generic `absent_family_prefix` is stale. Retain all blocking, symbol, family-group, and
zero-object assertions, but expect `current_unarchived`.

### 2. Typed temporal coverage retains official authority

`test_cost_calibration_requires_book_depth_and_ticker` uses source periods beginning
after the authenticated onboard period. The resulting nonblocking
`head_gap_family_launch` makes the source state `qualified_with_typed_gaps` and coverage
state `typed_gaps`; it does not make the official bookTicker/bookDepth authority
inaccessible or release-blocked. Preserve `official_complete`, official authority, both
family groups, and six listed objects, and assert the typed source/coverage states rather
than falsely demanding no temporal gap.

### 3. The oversized fixture is not fully inventoried

`test_oversized_object_emits_typed_sample_budget_block` supplies only monthly trades even
though the trade product declares both trades and aggregate-trades groups, and it uses
widely separated months that create interior gaps. Production correctly labels that
fixture inaccessible independently of the sample budget. Correct the fixture to include
at least one cadence for both required logical groups, use contiguous periods, and provide
affirmative current-perpetual membership. Make every relevant candidate exceed the
bounded sample-object allowance. Then retain the assertions that complete inventory size
is reported, a typed sample-budget block is emitted, no inaccessible authority is caused
by the budget alone, and no oversized payload is fetched as a sample.

### 4. A locked plan does not rewrite history on resume

`test_retained_object_is_reported_once` predates the immutable plan required by review 75.
The second run must replay the original plan, so its locked `unique_new_objects`,
`unique_retained_objects`, and `new_download_bytes` remain identical rather than being
rewritten from download to retained. Correct the test to preserve and compare the first
and second plan identities/counts, while separately asserting that execution reused the
checkpointed object without another raw fetch and that the cumulative ledger contains
only the original transfer.

### 5. The row test must supply an authenticated envelope

`test_exchange_info_row_missing_identity_fields_fails_closed` omits response-wide
`serverTime`, so parsing correctly fails on the unauthenticated envelope before inspecting
the row. Add a valid positive `serverTime` while retaining the incomplete row; then the
test can specifically require the missing contract-identity-field failure. Keep the
separate missing-server-time coverage.

## Bounded test-source authorization

Implementation Dev - Codex Spark using GPT-5.3-Codex-Spark High may modify only:

- `tests/acquisition/test_binance_usdm_harmonic_qualification.py`.

The correction is mechanical and must implement exactly the five dispositions above.
It must preserve Grok's review-79 tests, every previously accepted integrity test, and all
production semantics. Spark authors test source only. It performs no test execution,
production/CLI/fixture/data/repository-record edit, integration, Git operation, commit,
push, network run, purchase, deletion, catalog mutation, Gate 2, Nautilus, or Harmonic
Trader work. It stops for fresh reviewer inspection with the exact test SHA-256.

Hermes integration and every real rerun remain unauthorized until that source review.

## Publication set

Under the narrow reviewer governance exception, the reviewer may stage, commit, and push
exactly:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/82_CEX002_FOCUSED_TEST_FAILURE_REVIEW.md`; and
- `tickets/CEX-002.md`.

No source, test, fixture, data, prior record, or unrelated dirty path belongs to this
publication. The reviewer executes no tests or acceptance commands.

## Disposition

CEX-002 and Gate 1 remain `IN_PROGRESS`. Gate 2, Hermes integration, every real rerun,
Nautilus integration, every other ticket, and Harmonic Trader work remain unauthorized.
Next ticket remains `NONE`.
