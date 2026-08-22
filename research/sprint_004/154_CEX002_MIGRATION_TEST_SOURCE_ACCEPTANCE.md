# CEX-002 Migration Test Source Acceptance

Date: 2026-08-21

Reviewer: Lead Quantitative Finance Researcher/Engineer

Governing review: `research/sprint_004/153_CEX002_MIGRATION_FOCUSED_FAILURE_REVIEW.md`

## Accepted source identities

| Path | SHA-256 | Decision |
|---|---|---|
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `a753afc0290708c630198714d574f1ddb65fa43e97b516a100ba32f0a915fd1e` | accepted and frozen |
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `ee9a794d96671763a6321373d70e3ed67d5c2f0c234ba94a234fd14308a9aae5` | unchanged, accepted, frozen |
| `scripts/research/qualify_binance_usdm_harmonic_sources.py` | `3b9181366ee4a575d450d06cf70340e1a2cf2c65d5239081f4782ebc9c6e4ced` | unchanged, accepted, frozen |

The test path contains 285 unique `test_` function definitions. Its worktree diff is 24
insertions and 6 deletions; `git diff --check` is clean. The reviewer ran no test, Ruff,
migration, candidate, network, or data command.

## Decision

**ACCEPT AND FREEZE THE EXACT TEST CORRECTION; AUTHORIZE HERMES FOR TEST INTEGRATION, A
FULL FOCUSED-COMMAND RESTART, AND CONDITIONAL REVIEWED MIGRATION-ONLY EXECUTION.**

Grok closes all three review-153 findings without changing production or CLI source:

- `_accepted_v4_candidate()` seeds version 2 from one real month and constructs the
  candidate from the full three-month index, so the real planner yields at least two
  download entries and at least one retained entry;
- the fixture patches each generated authority constant in both the production module and
  the test module for that test's monkeypatch lifetime, while the independent literal test
  remains unpatched and continues to prove the production values; and
- the wrong-authority ledger test supplies a valid typed source receipt, changes only the
  plan digest, and expects the exact binding-validator error.

No assertion strength, production validation, production literal, or migration authority
is reduced.

## Hermes integration

Jr Dev - Hermes first establishes `HEAD == origin/main` at this review-publication commit.
It rehashes all three accepted paths above and confirms 285 unique test definitions. A
mismatch stops before staging.

Hermes stages exactly
`tests/acquisition/test_binance_usdm_harmonic_qualification.py`, commits and pushes one
test-correction integration commit, proves `HEAD == origin/main`, and proves the index is
empty. It stages no source, CLI, control, review, report, fixture, ignored evidence,
database sidecar, or unrelated dirty path. It makes no source/test edit and uses no reset,
restore, checkout, stash, clean, or equivalent worktree rewrite.

## Full focused restart

Only after the integration commit is pushed, Hermes restarts review 151's complete command
sequence from C1 and stops at the first nonzero exit:

1. `.venv/bin/python -m pytest tests/acquisition/test_binance_usdm_harmonic_qualification.py -q --tb=short`
2. `.venv/bin/python -m pytest tests/test_download_atomicity.py -q --tb=short`
3. `.venv/bin/python -m ruff check src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py scripts/research/qualify_binance_usdm_harmonic_sources.py src/source_audit/download.py tests/acquisition/test_binance_usdm_harmonic_qualification.py tests/test_download_atomicity.py`
4. `python3 scripts/check_repo_control.py`
5. `git show --check --oneline --no-renames HEAD`

Hermes retains actual pytest pass/collection evidence and exact exit/output for every
command. Any failure prevents migration preconditions and execution.

## Conditional migration execution

Only if C1-C5 all return exit 0, Hermes performs every migration precondition, the exact
single foreground `--apply-reviewed-v4-migration-only` invocation, and every after-proof
specified in review 151. All review-151 accepted report, version-2 lock, legacy ledger,
amendment-ledger absence, sample-checkpoint, raw-tree, manifest-detail, receipt, authority,
mutation, status, and no-download requirements remain binding without substitution.

Status 2 remains the expected terminal qualification status after a successful migration.
Every status stops after the one invocation. Hermes runs no retry, ordinary resume, second
migration, or sample acquisition.

## Record and publication

Hermes writes `research/sprint_004/155_CEX002_MIGRATION_TEST_INTEGRATION_AND_EXECUTION.md`
with the test-integration commit, all command evidence or stop point, migration
preconditions, the one invocation and receipt if authorized, complete after-proof,
mutations, deviations, and terminal state.

After the invocation or any safe stop, Hermes updates both controls to `Next required
actor: Lead Quantitative Finance Researcher/Engineer - inspect record 155`, stages exactly
the two controls and record 155, commits and pushes, proves `HEAD == origin/main`, and
stops. It never stages data, state, cache, report, manifest-detail, database sidecar, or
unrelated dirty paths.

## Boundaries

No production/CLI edit, source/test edit after integration, command skip, retry, ordinary
resume, second migration, sample acquisition, Gate 2, normalization, catalog publication,
Nautilus work, Harmonic Trader work, payoff analysis, PAPER, LIVE, paid source, external
artifact service, reduced scope, or unrelated dirty-path mutation is authorized.

## Disposition

CEX-002 remains `IN_PROGRESS`. Gate 1 has not passed. Next ticket remains `NONE`.
