# CEX-002 Migration Ruff Source Acceptance

Date: 2026-08-21

Reviewer: Lead Quantitative Finance Researcher/Engineer

Governing review: `research/sprint_004/156_CEX002_MIGRATION_RUFF_FAILURE_REVIEW.md`

## Accepted source identities

| Path | SHA-256 | Decision |
|---|---|---|
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `5d4b2e2c199b6826e9da6d6561381207644d33c119572995c7211d5cead1c6d4` | accepted and frozen |
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `ee9a794d96671763a6321373d70e3ed67d5c2f0c234ba94a234fd14308a9aae5` | unchanged, accepted, frozen |
| `scripts/research/qualify_binance_usdm_harmonic_sources.py` | `3b9181366ee4a575d450d06cf70340e1a2cf2c65d5239081f4782ebc9c6e4ced` | unchanged, accepted, frozen |

The test path contains 285 unique `test_` function definitions. Its entire worktree diff
deletes only the five imports enumerated in review 156, and `git diff --check` is clean.
The reviewer ran no test, Ruff, migration, candidate, network, or data command.

## Decision

**ACCEPT AND FREEZE THE EXACT FIVE-IMPORT CLEANUP; AUTHORIZE HERMES FOR INTEGRATION, A FULL
FOCUSED RESTART, AND CONDITIONAL REVIEWED MIGRATION-ONLY EXECUTION.**

The deletion is behavior-neutral. The interruption tests still reach the relevant helpers
through the imported production module, while no direct use of any deleted name remains.
Review 155's exit-0 C1 and C2 evidence remains valid historical evidence, but a fresh
post-integration sequence is required before migration.

## Hermes integration and commands

Jr Dev - Hermes first establishes `HEAD == origin/main` at this review-publication commit,
rehashes all three accepted paths above, and confirms 285 unique test definitions. A
mismatch stops before staging.

Hermes stages exactly the CEX test path, commits and pushes one cleanup integration commit,
proves `HEAD == origin/main`, and proves the index is empty. It stages no production, CLI,
control, review, report, fixture, ignored evidence, database sidecar, or unrelated dirty
path; makes no source/test edit; and uses no worktree-rewriting Git operation.

It then runs the full stop-on-first-failure sequence from C1:

1. `.venv/bin/python -m pytest tests/acquisition/test_binance_usdm_harmonic_qualification.py -q --tb=short`
2. `.venv/bin/python -m pytest tests/test_download_atomicity.py -q --tb=short`
3. `.venv/bin/python -m ruff check src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py scripts/research/qualify_binance_usdm_harmonic_sources.py src/source_audit/download.py tests/acquisition/test_binance_usdm_harmonic_qualification.py tests/test_download_atomicity.py`
4. `python3 scripts/check_repo_control.py`
5. `git show --check --oneline --no-renames HEAD`

Hermes retains actual pytest evidence and exact exit/output for every command. Any failure
prevents migration preconditions and execution.

## Conditional migration and publication

Only if C1-C5 all return exit 0, Hermes performs every precondition, the exact single
foreground `--apply-reviewed-v4-migration-only` invocation, and every after-proof in
review 151. Status 2 remains the expected successful terminal qualification status. Every
status stops after that invocation; no retry, ordinary resume, second migration, or sample
acquisition is authorized.

Hermes writes `research/sprint_004/158_CEX002_MIGRATION_RUFF_INTEGRATION_AND_EXECUTION.md`
with the cleanup integration commit, complete command evidence or stop point, migration
preconditions, invocation/receipt if authorized, after-proof, mutations, deviations, and
terminal state. It updates both controls to `Next required actor: Lead Quantitative Finance
Researcher/Engineer - inspect record 158`, stages exactly the two controls and record 158,
commits and pushes, proves `HEAD == origin/main`, and stops. It never stages data, state,
cache, report, manifest detail, database sidecar, or unrelated dirty paths.

## Boundaries

No production/CLI edit, source/test edit after integration, command skip, retry, ordinary
resume, second migration, sample acquisition, Gate 2, normalization, catalog publication,
Nautilus work, Harmonic Trader work, payoff analysis, PAPER, LIVE, paid source, external
artifact service, reduced scope, or unrelated dirty-path mutation is authorized.

## Disposition

CEX-002 remains `IN_PROGRESS`. Gate 1 has not passed. Next ticket remains `NONE`.
