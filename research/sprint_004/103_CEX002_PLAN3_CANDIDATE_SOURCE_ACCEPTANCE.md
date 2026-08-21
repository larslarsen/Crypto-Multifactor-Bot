# CEX-002 Plan-3 Candidate Source Acceptance

Date: 2026-08-20

Reviewer: Lead Quantitative Finance Researcher/Engineer

Reviewed base: `820145eb36712800fd739ca185fb3823c115ac75`

Accepted source/test hashes:

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `ee142aabf0a3df589940ab982ff0087f9deacc593517fe856af9760a900c5bcd` |
| `scripts/research/qualify_binance_usdm_harmonic_sources.py` | `7c60f4d5bd7eacf9f0b85bac4a5d356106d035a5613e2a4e38163697906822d8` |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `6b3949e6e428e85e14febaf6a6725c487975da3e8421e206ed904442f08f7f1e` |

The 17 existing fixture files are unchanged. Static counting finds 170 test functions and
no duplicate names.

## Decision

**ACCEPT SOURCE FOR JR INTEGRATION AND ONE CANDIDATE-ONLY REAL EXECUTION.**

The CLI correction closes review 102. `--candidate-plan-only` calls the accepted read-only
preflight before reading `COINALYZE_API_KEY`, creating `store_root`, constructing transport
objects, or loading/bootstrapping listing, checkpoint, or retry state. Invalid authority
uses the existing redacted `ERROR:` contract and returns 1. Normal initialization remains
under the candidate branch rather than being removed, and production independently repeats
the preflight before its own mutable facilities.

The behavioral test loads and invokes the actual CLI `main`, corrupts current authority to
version 3, replaces every downstream facility with a forbidden sentinel, recursively hashes
files and records directories, and proves exit 1, no report, no facility call, byte/tree
identity, and no secret output. A second bounded static assertion preserves ordinary
initialization and its ordering. The accepted production hash from review 102 and all
fixtures remain byte-identical.

The reviewer ran no pytest, Ruff, control/acceptance command, network/data command,
migration, or real qualification. This is source acceptance only; the version-3 candidate
and Gate 1 data evidence are not yet accepted.

## Hermes Integration

Jr Dev - Hermes first establishes `HEAD == origin/main` at the review-103 publication
commit and verifies all three accepted hashes plus the unchanged fixture directory. It
stages exactly the three accepted Python paths above, commits them as a forward-preserved
source integration, pushes, and re-establishes `HEAD == origin/main`. No unrelated dirty
path, fixture, data file, report, control file, or database sidecar belongs to that commit.

No restore, reset, checkout, stash, clean, deletion, reconstruction, or relock is
authorized. A later failure is corrected forward from the preserved source commit.

## Focused Commands

Hermes then runs in order:

1. `.venv/bin/python -m pytest tests/acquisition/test_binance_usdm_harmonic_qualification.py -q --tb=short`
2. `.venv/bin/python -m pytest tests/test_download_atomicity.py -q --tb=short`
3. `.venv/bin/python -m ruff check src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py scripts/research/qualify_binance_usdm_harmonic_sources.py tests/acquisition/test_binance_usdm_harmonic_qualification.py`
4. `python3 scripts/check_repo_control.py`
5. `git show --check --oneline --no-renames HEAD`

The full suite remains deferred to final CEX-002 release acceptance because unrelated dirty
DEX/BitMEX work is excluded from this integration. No `-k` substitution, source/test edit,
clean-worktree reconstruction, or DEX/BitMEX command is authorized. Any failure stops before
the real candidate run and is recorded verbatim in record 104.

## Candidate-Only Execution

After all five commands pass, Hermes records before-state evidence for:

- exact SHA-256 of `data/cex002_qualify/cex002_sample_plan_lock.json`;
- exact SHA-256 of `data/cex002_qualify/cex002_budget_ledger.json`;
- a deterministic recursive path/size/content digest plus file count and bytes for
  `data/cex002_qualify/raw/sha256`;
- absence/presence and, if unexpectedly present, SHA-256 of
  `data/cex002_qualify/cex002_amendment_ledger.json`; and
- current report SHA-256 and size.

Hermes loads `.env` only into the environment, never prints the key or places it in an
argument, and invokes exactly once:

```bash
set -a
. ./.env
set +a
.venv/bin/python scripts/research/qualify_binance_usdm_harmonic_sources.py \
  --store-root data/cex002_qualify \
  --progress-path data/cex002_qualify/cex002_qualification_progress.json \
  --report-path research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json \
  --candidate-plan-only
candidate_status=$?
```

The actual process exit status is captured immediately. Exit 1 stops and is not retried.
Exit 0 or 2 permits evidence publication but is not plan migration, acquisition, Gate-1
acceptance, or success by itself.

After the process, Hermes repeats every before-state measurement. The exact lock SHA,
ledger SHA, and raw-tree digest/count/bytes must match; the amendment ledger must remain
absent; `samples` must be empty; and the report must state `migration_authorized=false` and
`download_authorized=false`. Any mismatch is a failure and stops.

## Execution Record

Hermes creates `research/sprint_004/104_CEX002_PLAN3_CANDIDATE_EXECUTION.md` containing:

- source integration commit and all accepted hash checks;
- every command, exit status, collected/passed count, elapsed time, and material output;
- all before/after authority, raw-tree, amendment, and report identities;
- actual process exit, report SHA-256/bytes, gate state, acceptance flag, and blockers;
- candidate version/state, prior version/history/digests, plan-content digest, envelope
  digest, input identities, plan entry/blocked/new/retained counts and bytes, and allowance;
- acquisition-manifest selected/pending/consumable/collision/rejection and per-family counts;
- selected raw, cost-sample, projected-new, largest-object, available-space, unknown later
  storage components, and total-sufficiency state;
- confirmed/unresolved membership, full unresolved identities/classes, Coinalyze mapping and
  typed gaps, taker-flow evidence, holdout boundary, listing/retry evidence, and sample count;
  and
- an explicit statement that no plan/ledger migration, sample download, amendment-ledger
  creation, Gate 2, normalization, catalog publication, or model work occurred.

Hermes then changes both control files to
`Lead Quantitative Finance Researcher/Engineer - inspect review-104 candidate execution`,
adds record 104 to the governing documents, and leaves next ticket `NONE`. It stages and
commits exactly:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json` only if the real command ran;
- `research/sprint_004/104_CEX002_PLAN3_CANDIDATE_EXECUTION.md`; and
- `tickets/CEX-002.md`.

It pushes, establishes `HEAD == origin/main`, and stops for reviewer inspection. No other
path belongs to the execution publication.

## Disposition

CEX-002 remains `IN_PROGRESS`. Gate 1 has not passed. Plan-3 mutation, sample acquisition,
Gate 2, normalization, catalog publication, Nautilus execution, other-ticket work, Harmonic
Trader work, payoff analysis, PAPER, and LIVE remain unauthorized. Next ticket remains
`NONE`.
