# CEX-002 Holdout Record-Path Failure Review

Date: 2026-08-20

Reviewer: Lead Quantitative Finance Researcher/Engineer

Reviewed source integration:
`b062f1bd094d46fbcd7b31713763c698e87507b4`

Reviewed execution publication:
`5e14414fa5433c82b664f6ce199d55a6eb9e25a6`

Integrated hashes:

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `23e25e6f63189a7b381450f7b7fd0187a78da6ca169eff1d4acdf588b0b75daf` |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `4ef66b0e527e890956075d7565601821eed7fab59307a11339d4e1afffb7e692` |
| `scripts/research/qualify_binance_usdm_harmonic_sources.py` | `7c60f4d5bd7eacf9f0b85bac4a5d356106d035a5613e2a4e38163697906822d8` |

## Decision

**ACCEPT THE EXACT INTEGRATION AND STOP DISCIPLINE. REJECT THE FOCUSED EXECUTION.
AUTHORIZE ONE SOURCE-ONLY CLAUDE CORRECTION.**

Hermes integrated and pushed exactly the two review-109 paths. Focused command 1 collected
189 cases and returned exit 1 with 187 passed and 2 failed. Hermes correctly ran no later
focused command and did not invoke the real candidate process. No real candidate report,
version-3 proposal, or Gate-1 evidence exists to review.

## Finding - local holdout path is execution-plane identity

Both failures now pass the same semantic holdout instant and differ at a single `c` versus
`r` byte. The only `record_path` field in the production module is
`HoldoutBoundary.to_dict()["record_path"]`, whose value contains the local store root:
`.../clean/...` versus `.../resumed/...`. That filesystem location says where the durable
record is stored, not what prospective boundary was pinned.

Review 108 correctly preserved `boundary_utc`, `boundary_ms`, `boundary_id`, `pinned_at`,
`prior_record_sha256`, and `replay_rule` as semantic identity, but incorrectly froze the
local `record_path` with them. This is a reviewer classification error.

The correction is exact: add `record_path` to `_IDENTITY_DROP_KEYS`. It is the only
`record_path` key in this module. Do not drop or change any boundary time, identifier,
lineage digest, replay rule, state, or outcome-blind assertion. Do not change
`HoldoutBoundary`, its durable document, or either failing test. The complete identity
comparisons remain the acceptance contract and must pass because only the local filesystem
location is excluded.

## Claude authorization

Sr Dev - Claude Build using Claude Opus 5 is authorized to edit exactly:

- `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py`.

Claude adds only `record_path` to the execution-plane identity drop-key set with a concise
comment that the semantic holdout fields remain included. The test path, CLI, all 17
fixtures, manifest selection, final proof rebuild, taker-flow logic, holdout implementation,
locked plan, budget/ledger behavior, and every other source contract are frozen.

Claude performs no tests, Ruff, repo-control command, network/data run, migration,
integration, repository-record edit, Git operation, acquisition, catalog work, Nautilus
work, Harmonic Trader work, or publication. It stops for reviewer inspection and returns
the exact source SHA-256. Hermes and the real candidate execution remain unauthorized.

## Reviewer publication

This review is a narrow reviewer-authored governance publication. The reviewer may stage,
commit, and push exactly:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/111_CEX002_HOLDOUT_RECORD_PATH_FAILURE_REVIEW.md`; and
- `tickets/CEX-002.md`.

No source, test, fixture, data, report, database sidecar, or unrelated dirty path belongs
to that commit. The reviewer ran no pytest, Ruff, repo-control, acceptance, network, data,
or migration command.

## Disposition

CEX-002 remains `IN_PROGRESS`. Gate 1 has not passed. Real candidate execution, Plan-3
mutation, sample acquisition, Gate 2, normalization, catalog publication, Nautilus work,
Harmonic Trader work, payoff analysis, PAPER, LIVE, and every other ticket remain
unauthorized. Next ticket remains `NONE`.
