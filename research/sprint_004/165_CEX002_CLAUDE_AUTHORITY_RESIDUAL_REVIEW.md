# CEX-002 Claude Authority Residual Review

Date: 2026-08-21

Reviewer: Lead Quantitative Finance Researcher/Engineer

Governing review: `research/sprint_004/164_CEX002_CLAUDE_SEMANTIC_AUTHORITY_SOURCE_REVIEW.md`

## Reviewed source identities

| Path | SHA-256 | Decision |
|---|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `5a98e442a62ee7d9da4c3007aa0b737d927d0c40aefd63ce2c775082a7f9bd9f` | residual correction required |
| `scripts/research/qualify_binance_usdm_harmonic_sources.py` | `473185ca946dcc37d506d8891e8f955708ff80c976a586967762c1294956d28f` | accepted and frozen |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `cd4238724998db527ca908426dc49435e69725535e361d7429496db18ed34c4d` | residual correction required |

The test path contains 302 unique `test_` function definitions. The exact three-path diff
is whitespace-clean and repository control passes. The reviewer ran no test, Ruff,
network/data, transaction, migration, or ordinary qualification command.

## Decision

**ACCEPT AND FREEZE THE QUOTE, MEMBERSHIP, GATE/RELEASE, AND CLI CORRECTIONS; REJECT THE
SOURCE-AUTHORITY TRANSACTION BEFORE INTEGRATION; AUTHORIZE ONE TWO-PATH CLAUDE RESIDUAL.**

The dedicated CLI path now returns before facility construction, prints both blocker
domains, and passes no caller-selected source identity. The production matrix explicitly
clears the qualified Coinalyze source blocker, carries derived taker flow's actual release
state, and includes derived release blockers. The dataclass imports, and the quote rule now
matches ADR-0020. Those regions are accepted and frozen.

The one-shot transaction still cannot complete, and its exact-state checks remain weaker
than review 164 requires. Hermes remains unauthorized.

## Findings

### 1. Complete-state proof rejects the lock it just wrote

The preserved lock is the raw checkpoint document and therefore contains the envelope
fields `ticket`, `kind`, and `version`. `_require_single_lock_transform()` compares every
field in that document against `SamplePlanLock.to_dict()`, which contains only the lock
body. The first comparison of an envelope field fails.

Consequently a fresh invocation can preserve evidence, append and flush the ledger
receipt, and publish the corrected lock, but its mandatory final preflight then raises
instead of returning a receipt. Every rerun fails the same complete-state proof. This is a
post-mutation terminal failure, not a cosmetic assertion issue.

Use the existing checkpoint parser or an exact accepted `SamplePlanLock` body for the
comparison. Add a focused assertion that the real envelope is normalized exactly once and
that the transaction returns only after complete state re-proves.

### 2. Retained-evidence locations remain caller authority

`apply_reviewed_source_correction()` accepts optional `sample_dir` and `sidecar_dir` paths.
Those arguments let a programmatic caller redirect the retained-evidence proof away from
the accepted store. The correction is pinned to the accepted store and report; its public
entry may accept only those paths plus an injectable time for deterministic tests. Raw and
sidecar roots must be derived from `store_root` internally.

### 3. Partial and complete states are not fully exact

The partial-state proof compares only binding, charges, and reservations with the accepted
ledger. A self-consistent change to legacy accounting fields or an added top-level field
can pass preflight; the code then advances the lock before the ordinary validator rejects
some such changes. The full live ledger document must equal the accepted canonical ledger
with exactly one receipt append and the corresponding integrity update, with no extra or
changed field.

The complete-lock proof is also one-directional. It does not reject extra budget-snapshot
fields or require exact values for `source_correction_id`, the two canonical evidence
paths, and the lock's amendment binding. Complete state must be the accepted lock plus the
single reviewed input/binding/metadata transform, in both directions, and must agree with
the advanced ledger before it is classified complete.

Finally, fresh execution uses `_atomic_publish()` directly for the prior ledger. A corrupt
file already present at that content address is overwritten rather than rejected before
mutation. Prior-ledger preservation must use collision-safe content-address verification,
including a rehash of the live accepted bytes at publication time.

### 4. The transaction tests do not yet exercise the claimed recovery

The interruption test calls `monkeypatch.undo()` after the injected lock-publication
failure. That removes all fixture-pinned report, lock, ledger, checkpoint, plan, legacy,
and source identities, then restores only the selector. Its recovery call therefore uses
production constants against the temporary fixture and cannot reach recovery.

The accepted-state fixture also stops immediately after migration and asserts an empty
amendment ledger. The real accepted state has 82 settled charges and two reservations.
The tests must carry nonempty settled and reserved accounting through fresh execution,
partial recovery, and idempotent replay byte-exact. They must also cover redirected
evidence arguments being impossible, corrupt pre-existing ledger evidence, altered legacy
or extra ledger fields, extra or wrong correction metadata, wrong evidence paths/binding,
and failure-before-mutation for every rejected form.

The gate-separation test must directly assert that derived taker flow's
`release_blocked` equals the bar row and that its membership in
`release_blocked_products` follows that value.

## Claude residual authorization

Sr Dev - Claude Build using Claude Opus 5 may edit only:

- `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py`; and
- `tests/acquisition/test_binance_usdm_harmonic_qualification.py`.

The CLI is frozen at the accepted hash above. Claude preserves every accepted quote,
membership, source/release, Coinalyze, derived-flow, CLI, plan, and accounting behavior.
It corrects only the four findings in this review:

1. normalize and compare the accepted lock body correctly so fresh execution, exact
   partial recovery, and complete idempotence all re-prove;
2. remove caller-selected retained-evidence roots and pin them beneath `store_root`;
3. prove the full partial ledger and full completed lock transform in both directions,
   validate exact correction metadata/binding/evidence paths, and reject a corrupt
   pre-existing content-address before any mutation; and
4. repair and complete the focused tests with nonempty charge/reservation preservation and
   explicit derived-release assertions.

Claude runs no command, test, Ruff, repository-control, network/data operation,
transaction, migration, ordinary qualification, Git operation, record/control/ADR edit,
commit, or push. It returns exact SHA-256 values for the two authorized paths, confirms the
CLI hash remains exact, and returns the unique CEX test-function count, then stops for
reviewer source inspection. Hermes remains unauthorized.

## Boundaries

No CLI edit, integration, live source-authority transaction, ordinary resume, reservation
reconciliation, Gate-1 acceptance, sizing, Gate 2, bulk acquisition, normalization,
catalog publication, Nautilus work, Harmonic Trader work, payoff analysis, PAPER, LIVE,
paid source, reduced scope, or next-ticket work is authorized.

## Disposition

CEX-002 remains `IN_PROGRESS`. Gate 1 has not passed. Next ticket remains `NONE`.
