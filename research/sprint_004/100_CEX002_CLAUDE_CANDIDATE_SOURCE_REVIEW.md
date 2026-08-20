# CEX-002 Claude Candidate Source Review

Date: 2026-08-20

Reviewer: Lead Quantitative Finance Researcher/Engineer

Reviewed base: `a1eee0eb1e415fbddad0158fe60cd74dcca1ef4d`

Reviewed source/test hashes:

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `c57784e955ef9dce6513b54262fe3dfd5192aac3d22a74dd1ccce5c81f4f8f5b` |
| `scripts/research/qualify_binance_usdm_harmonic_sources.py` | `444493eca6521c40b189cdec74b31946403230984185cb49495d71fc5da92b41` |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `669a6aeb35379d01d91c385043b83ef0a5f02eb99e399693c36f38d0f291a4ea` |

The existing 17 fixture files are unchanged. Static counting finds 160 test functions,
so the accumulated suite remains present.

## Decision

**REJECT BEFORE JR INTEGRATION. AUTHORIZE ONE SURGICAL CLAUDE CORRECTION.**

Claude closes most of review 99: candidate mode constructs a separate plan, asserts no
migration/download, skips the raw acquisition loop, reports a separate amendment identity,
serializes selected manifest rows and economic intervals, rejects explicit overlaps, keeps
Gate-2 total sufficiency unknown, pins a stable holdout boundary, fixes the dead collision
test, and adds focused source tests without truncating the accumulated suite.

Four control defects and one residual manifest-integrity defect remain. The reviewer ran
no tests, network/data command, migration, or real qualification. A path-scoped
`git diff --check` was inadvertently executed during static inspection and produced no
output; that command is void as integration evidence and does not replace Hermes's later
acceptance execution.

## Blocking Finding 1: Candidate mode can rewrite the legacy ledger before hashing it

Lines 6512-6526 still bootstrap and reconcile the legacy ledger unconditionally, before
the candidate/noncandidate branch. `BudgetLedger.reconcile` settles any now-proved
reservation through `settle`, which flushes the ledger at lines 2767-2831. Candidate mode
takes `prior_ledger_sha256` only later at line 6598. It can therefore rewrite the supposedly
read-only legacy ledger and then prove only that the already-rewritten bytes did not change
again.

The focused candidate test seeds a ledger with settled charges and no recoverable
reservation, so it cannot exercise this path. The report's
`not_reconciled_in_candidate_phase` claim and byte-unchanged assertions are false for the
exact crash-recovery state that the legacy ledger was designed to preserve.

## Blocking Finding 2: Candidate-mode taker flow cannot use retained schema evidence

Candidate mode deliberately executes no plan entries at line 6763, leaving `samples`
empty. The taker-flow derivation at lines 7017-7036 searches only that empty collection,
so the actual candidate report always returns sample-pending/unsupported even when its
retained kline object and schema have just been re-proved from the checkpoint.

The new taker-flow test runs normal acquisition mode, not `candidate_plan_only=True`, and
therefore does not test the report we are authorizing. Candidate mode must derive only from
re-proved retained schema evidence and remain honestly pending when that evidence is absent;
it must not download a sample to qualify the field.

## Blocking Finding 3: The candidate plan digest cannot become the locked plan digest

`candidate_plan_digest` at lines 2303-2306 hashes a domain-separated wrapper, while
`SamplePlanLock.lock_plan` continues to record `plan_content_digest(plan)`. The candidate
report calls the wrapper hash `plan_digest` and compares it to prior content digests at
lines 2324-2349. Those are different identity domains, so the comparison is vacuous and a
future exact version-3 lock would receive a different digest from the candidate the
reviewer inspected.

The focused test explicitly celebrates this mismatch. The comparable plan-content digest
must remain the plan digest. A separate candidate-envelope digest may bind allowance and
input identities, but it must not replace or conceal exact plan-content equality.

## Blocking Finding 4: Prior authority accepts versions later than version 2

The candidate precondition at lines 6579-6587 rejects only versions below 2. A current
version-3 or later lock is accepted as authority for another `plan_version = 3` candidate.
It also does not assert the accepted durable history containing versions 0 and 1. Review
98 requires exact preservation of versions 0 through 2, not any lock whose counter happens
to be at least 2.

The candidate path must require current version exactly 2, validate the expected unique
version-0/version-1 history and current version-2 digest identities, and reject every other
transition before any candidate-phase mutation.

## Residual Manifest Integrity Correction

The new manifest is inspectable, but `checksum_listed` means only that a sibling path was
present in an object listing. It does not mean the sidecar was parsed, bound to the object,
or that raw bytes matched it. Lines 2933-3033 nevertheless use that state to call a monthly
object canonical and a fallback daily object `consumable`.

The candidate manifest must distinguish sidecar-listing evidence, pending raw validation,
and checksum-proved retained evidence. It may select planned objects outcome-blindly, but
no unproved row may claim accepted/consumable integrity. Selected daily fallback must carry
the same explicit integrity precondition, and missing integrity authority must remain a
typed gap or block rather than silently becoming usable data.

## Surgical Claude Authorization

Sr Dev - Claude Build using Claude Opus 5 may edit only:

- `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py`;
- `scripts/research/qualify_binance_usdm_harmonic_sources.py` only if its candidate summary
  must distinguish the plan-content and candidate-envelope digests;
- `tests/acquisition/test_binance_usdm_harmonic_qualification.py`; and
- `tests/acquisition/fixtures/binance_usdm_harmonic_qualification/` only if one bounded
  checksum-sidecar fixture is required.

Claude preserves every review-100 accepted correction and changes only the findings above.
The drop must:

1. move all bootstrap/reconciliation/settlement behavior wholly outside candidate mode;
   candidate mode loads the legacy ledger read-only and hashes it before any operation that
   could mutate it;
2. test a proved outstanding legacy reservation and show the exact ledger and lock bytes
   remain unchanged, with no `settle`, `flush`, migration, amendment-ledger file, or raw
   fetch;
3. derive candidate-mode taker-flow state from re-proved retained kline checkpoint/schema
   evidence, with focused supported and honestly-pending cases and zero raw acquisition;
4. record `plan_content_digest(candidate_plan)` as the comparable plan digest, compare it
   with current and historical plan-content digests, and optionally add a separately named
   candidate-envelope digest for allowance/input identity; an identical old plan under a
   new allowance must not evade reuse detection, and an exact future lock must calculate
   the reviewed plan digest;
5. require current plan version exactly 2 and the expected unique version-0/version-1
   history before constructing version 3; versions 1, 3, later, missing, duplicated, or
   malformed history fail closed before candidate mutation; and
6. distinguish listed sidecar, pending raw validation, quarantined/rejected, and
   checksum-proved retained states in manifest rows. Bind the sidecar identity when known;
   do not label an unproved monthly or daily object consumable, and retain explicit
   fallback/gap evidence without overlapping selected coverage.

Claude performs no tests, network/data run, plan or ledger migration, integration,
repository-record edit, Git operation, sample download, bulk acquisition, catalog
mutation, Nautilus work, or Harmonic Trader work. It stops for reviewer source inspection
with exact hashes, the test-function count, and a concise change summary.

## Publication Set

Under the reviewer governance-publication exception, the reviewer may stage, commit, and
push exactly:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/100_CEX002_CLAUDE_CANDIDATE_SOURCE_REVIEW.md`; and
- `tickets/CEX-002.md`.

No source, test, fixture, data, generated report, database sidecar, or unrelated dirty
path belongs to this publication. The reviewer executes no further acceptance commands.

## Disposition

CEX-002 remains `IN_PROGRESS`. Hermes is unauthorized. Gate 1 has not passed. Gate 2,
real acquisition, normalization, catalog publication, Nautilus execution, other-ticket
work, Harmonic Trader work, payoff analysis, PAPER, and LIVE remain unauthorized. Next
ticket remains `NONE`.
