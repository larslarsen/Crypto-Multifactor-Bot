# CEX-002 Grok Resolution Source Review

Date: 2026-08-20

Reviewer: Lead Quantitative Finance Researcher/Engineer

Reviewed base: `10ede0767783165a4e756c98f0b5aadad15c2e42`

Reviewed source/test hashes:

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `c12afab649cd5ead8c030bdcd46758c08c8f59ada7728d8ae5e2bf0e8377d414` |
| `scripts/research/qualify_binance_usdm_harmonic_sources.py` | `211344a4011730ff6c3aefb7365eb9b4885e435058e7fcabd7098a0d5cc6f8a5` |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `25e3baf5da1e12a8d2330d72fda469a48146f4726343475d8f3f3403d1370c0b` |

The existing 17 fixture files are unchanged.

## Decision

**REJECT BEFORE JR INTEGRATION. ROUTE ONE BOUNDED CORRECTION TO SR DEV - CLAUDE
BUILD USING CLAUDE OPUS 5.**

The drop correctly moves the declared archive products to native one-hour klines,
retains five-minute metrics and funding, separates discovery-only trade families,
constructs the intended bounded daily book sample, and changes affirmative Coinalyze
non-mappings into typed nonblocking intersection gaps. The complete accumulated test
file also remains present: static counting finds 148 test functions versus 140 at the
reviewed base.

Those useful changes are not integration-ready because the candidate-plan, immutable
manifest, holdout, and storage gates do not implement review 98 or ADR-0017. The reviewer
ran no tests, network/data command, migration, or acceptance command.

## Blocking Finding 1: The version-3 candidate is the executing old plan

`run_source_qualification` still owns the old lock-and-execute path. On a fresh store it
writes a version-1 lock at lines 6050-6103 and then acquires its download entries at lines
6135-6225. On the preserved store it reloads the existing locked plan at line 6105 and
either rejects the changed v3 code/config inputs at lines 6117-6127 or replays that old
plan. It never constructs an independent version-3 candidate.

The report then labels the same `plan` object as `candidate_unmigrated` at lines
6831-6855. Its reuse check compares only history versions 1 and 2 and omits the current
lock digest, so a fresh-store test reports `digest_reuses_prior = false` even though the
candidate digest is the just-written current-plan digest. The purported prior-lock hash
is also calculated after that fresh lock can be written. This is plan mutation and
acquisition, not a candidate-only amendment.

## Blocking Finding 2: The amendment allowance is not separately ledgered

Both budget constants are the same 268,435,456-byte value at lines 410-412, but the run
still bootstraps the sole legacy `cex002_budget_ledger.json` at lines 5846 and 6017-6031,
subtracts its prior spend when planning, reconciles it, and flushes it. Lines 6824-6851
only add amendment labels to the legacy-ledger report. They do not create a separate
amendment accounting identity, preserve that new allowance independently, or prove the
legacy ledger byte-identical. The accepted 1,015,198,547-byte legacy evidence therefore
cannot coexist with the claimed new allowance under this implementation.

## Blocking Finding 3: The acquisition manifest is neither integrity-qualified nor inspectable

`select_nonoverlapping_objects` treats the presence of any listed monthly object as
canonical at lines 2748-2801. It has no provider-checksum or schema/economic-validation
state, so all daily dates in that month disappear before the monthly object is accepted.
There is no path that quarantines an invalid monthly object and selects explicit daily
fallback coverage as ADR-0017 requires.

Although `build_acquisition_manifest` holds keys internally, both serialized manifest
surfaces at lines 6745-6751 and 6858-6863 omit every selected key, symbol, source family,
checksum identity, byte size, and economic interval. A count and cadence label cannot be
frozen, inspected for interval overlap, or used as an immutable acquisition authority.

## Blocking Finding 4: Taker-flow availability is asserted but never derived

`kline_schema_supports_taker_flow` exists at lines 2739-2741 but is never called by
production code. The trade-flow product is treated as an unevaluated derived output with
`coverage_state = not_applicable` at lines 6376-6379, rather than inheriting qualified
one-hour kline schema and coverage. Its only new test calls the helper against a hard-coded
schema constant. The report therefore does not establish that the selected bar source
supports the required hourly taker-flow product.

## Blocking Finding 5: Gate 2 can still be reported sufficient while total storage is unknown

`storage_feasibility` derives `gate2_storage_state = sufficient` from compressed raw
capacity alone at lines 3307-3363. The report later overlays unknown normalized,
temporary, reserve, and total fields without replacing that state at lines 6752-6767, and
the CLI prints the misleading Gate-2 state at lines 175-183. ADR-0017 explicitly says
unknown total requirements cannot pass Gate 2.

## Blocking Finding 6: No holdout boundary is pinned

`prospective_holdout_record` at lines 2961-2970 returns only the string
`pinned_before_model_outcomes`. It records no boundary time, durable identity, prior
record hash, or stable replay rule. Calling a state pinned does not create an immutable
prospective boundary or prove honest later retrieval/availability clocks.

## Blocking Finding 7: Focused tests encode the defects and include a dead collision case

`test_candidate_plan_v3_is_not_a_lock_mutation` at lines 3996-4011 starts with an empty
temporary store and affirmatively expects the unauthorized new version-1 lock. It does
not begin from the preserved version-2 lock and ledger, compare their bytes before and
after, or prove zero sample retrieval.

`test_duplicate_selected_month_is_an_economic_collision` uses a second filename ending
`2020-01-alt.zip` at lines 3932-3941. That name cannot match `_OBJECT_PERIOD_RE`, so static
inspection shows the object is ignored rather than classified as the asserted duplicate
month. No test execution is needed to establish that the case cannot reach the collision
branch.

The new tests do not bind a separate amendment ledger, exact manifest rows and intervals,
checksum-invalid monthly fallback, production taker-flow lineage, a durable holdout
identity, or Gate-2 unknown-state behavior.

## Claude Correction Authorization

Sr Dev - Claude Build using Claude Opus 5 may edit only:

- `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py`;
- `scripts/research/qualify_binance_usdm_harmonic_sources.py`;
- `tests/acquisition/test_binance_usdm_harmonic_qualification.py`; and
- `tests/acquisition/fixtures/binance_usdm_harmonic_qualification/` only for bounded
  focused fixtures required by these corrections.

Claude preserves Grok's accepted product/family, one-hour interval, cost-sample, storage-
field, and Coinalyze-gap direction and corrects only the seven findings above. The drop
must:

1. load the durable version-2 plan lock and legacy budget as read-only prior authority,
   construct a real version-3 candidate independently, and prove their exact bytes do not
   change; absence of required prior authority fails closed rather than fabricating
   versions 0 through 2;
2. include the full candidate plan, prior-lock hash, new stable input hashes, a digest
   distinct from the current and historical plan digests, explicit no-migration/no-download
   assertions, and no public relock switch;
3. model the 268,435,456-byte architecture-amendment allowance under a distinct ledger
   identity without reconciling, rewriting, or charging the legacy ledger in this phase;
   compatible checksum-proved retained objects remain reusable without erasing the legacy
   1,015,198,547-byte record;
4. emit immutable selected-manifest rows binding key, family, symbol, cadence, byte size,
   checksum/integrity state, and economic interval; accept monthly coverage only after
   required integrity evidence, use explicit daily fallback for uncovered or rejected
   monthly intervals, and fail closed on overlapping selected coverage;
5. derive and report the hourly taker-flow source/coverage state from the qualified native
   one-hour kline schema and interval coverage, without trades or `aggTrades`;
6. keep Gate-2 storage state unproved/unknown whenever normalized, temporary high-water,
   reserve, or total capacity is unknown, including the CLI summary;
7. create an actual durable, stable, outcome-blind holdout boundary identity with honest
   retrieval/source-availability semantics and no stream collector; and
8. add focused test source starting from representative version-2 lock/ledger authority,
   asserting their byte identity, zero raw-sample retrieval, distinct candidate identity,
   exact manifest/fallback/collision behavior, taker-flow lineage, stable holdout replay,
   and unknown Gate-2 state. Preserve every accumulated test and correct the dead collision
   fixture name.

Claude performs no tests, network/data run, plan or ledger migration, integration,
repository-record edit, Git operation, sample download, bulk acquisition, catalog
mutation, Nautilus work, or Harmonic Trader work. It stops for reviewer source inspection
with exact hashes, the test-function count, and a concise change summary.

## Publication Set

Under the reviewer governance-publication exception, the reviewer may stage, commit, and
push exactly:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/99_CEX002_GROK_RESOLUTION_SOURCE_REVIEW.md`; and
- `tickets/CEX-002.md`.

No source, test, fixture, data, generated report, database sidecar, or unrelated dirty
path belongs to this publication. The reviewer executes no tests or acceptance commands.

## Disposition

CEX-002 remains `IN_PROGRESS`. Hermes is unauthorized. Gate 1 has not passed. Gate 2,
real acquisition, normalization, catalog publication, Nautilus execution, other-ticket
work, Harmonic Trader work, payoff analysis, PAPER, and LIVE remain unauthorized. Next
ticket remains `NONE`.
