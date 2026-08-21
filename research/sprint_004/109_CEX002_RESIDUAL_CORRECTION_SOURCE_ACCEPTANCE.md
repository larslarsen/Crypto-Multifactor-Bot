# CEX-002 Residual Correction Source Acceptance

Date: 2026-08-20

Reviewer: Lead Quantitative Finance Researcher/Engineer

Reviewed base: `5a4f4800122ddc4345959c54510f4a0999c1bdd6`

Accepted source/test hashes:

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `23e25e6f63189a7b381450f7b7fd0187a78da6ca169eff1d4acdf588b0b75daf` |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `4ef66b0e527e890956075d7565601821eed7fab59307a11339d4e1afffb7e692` |

Frozen CLI hash:
`7c60f4d5bd7eacf9f0b85bac4a5d356106d035a5613e2a4e38163697906822d8`

The 17 tracked fixtures remain unchanged. Static counting finds 170 uniquely named test
functions and no duplicate names.

## Decision

**ACCEPT THE REVIEW-108 CORRECTION FOR JR INTEGRATION AND RESTARTED FOCUSED EXECUTION.**

This is static source acceptance only. The reviewer ran no pytest, Ruff, repo-control,
acceptance, network, data, or migration command. The focused suite, real candidate report,
version-3 candidate, and Gate-1 evidence are not yet accepted.

## Accepted correction

`object_integrity_state` now applies the required outcome-blind precedence: quarantine
first, then listed-sidecar absence, then proof within the listed-sidecar domain, then
listed/pending state. A retained or current-run proof cannot make an object whose provider
sidecar was absent from the pinned listing selectable. It therefore cannot replace a daily
fallback with an ineligible monthly package or change cadence selection after execution.
The final report-facing proof rebuild, provider-sidecar re-proof, locked plan, ledger, and
execution order remain unchanged.

The unit contract proves that a key in `proved_keys` with an empty `checksum_keys` set
remains `sidecar_absent` and unselected. The existing end-to-end daily-fallback assertion
remains unchanged.

The two cross-root identity tests now pin the same explicit timezone-aware first
qualification instant for each independently created store. Resumed invocations continue
to load the durable boundary without receiving a replacement time. Full `identity_bytes`
comparisons remain intact; the prospective holdout, identity drop-key set, and holdout
implementation are unchanged.

## Hermes integration

Jr Dev - Hermes first establishes `HEAD == origin/main` at the review-109 publication
commit. It verifies the two accepted hashes, the frozen CLI hash, and the unchanged fixture
directory. It stages exactly the two accepted source/test paths, commits them as a forward
correction, pushes, and re-establishes `HEAD == origin/main`.

No unrelated dirty path, fixture, data file, report, control file, or database sidecar
belongs to that source-integration commit. No restore, reset, checkout, stash, clean,
deletion, reconstruction, or relock is authorized.

## Focused commands

Hermes then runs exactly these commands in order:

1. `.venv/bin/python -m pytest tests/acquisition/test_binance_usdm_harmonic_qualification.py -q --tb=short`
2. `.venv/bin/python -m pytest tests/test_download_atomicity.py -q --tb=short`
3. `.venv/bin/python -m ruff check src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py scripts/research/qualify_binance_usdm_harmonic_sources.py tests/acquisition/test_binance_usdm_harmonic_qualification.py`
4. `python3 scripts/check_repo_control.py`
5. `git show --check --oneline --no-renames HEAD`

Any nonzero exit stops immediately. Hermes runs no subsequent command in the list and no
real candidate process after a failure. It records the exact stop in record 110. Results
after a failed predecessor are not acceptance evidence, and a later corrected sequence
must restart from command 1.

The full repository suite remains deferred to final CEX-002 release acceptance because
unrelated dirty DEX/BitMEX work is outside this integration. No `-k` substitution, source
or test edit, clean-worktree reconstruction, or DEX/BitMEX command is authorized.

## Candidate-only execution

Only after all five focused commands pass, Hermes captures before-state evidence for:

- exact SHA-256 of `data/cex002_qualify/cex002_sample_plan_lock.json`;
- exact SHA-256 of `data/cex002_qualify/cex002_budget_ledger.json`;
- deterministic recursive path/size/content digest, file count, and bytes for
  `data/cex002_qualify/raw/sha256`;
- absence or presence and SHA-256 of
  `data/cex002_qualify/cex002_amendment_ledger.json`; and
- current report SHA-256 and size.

Hermes loads `.env` only into the environment, never prints the key or puts it in an
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

Hermes captures the process status immediately. Exit 1 stops and is not retried. Exit 0 or
2 permits evidence publication but is not migration, acquisition, Gate-1 acceptance, or
success by itself.

Hermes repeats every before-state measurement. The exact version-2 lock SHA, legacy-ledger
SHA, and raw-tree digest/count/bytes must match; the amendment ledger must remain absent;
`samples` must be empty; and the report must state `migration_authorized=false` and
`download_authorized=false`. Any mismatch is a failure and stops.

## Execution record

Hermes creates `research/sprint_004/110_CEX002_PLAN3_CANDIDATE_EXECUTION.md` and records:

- source integration commit and every accepted/frozen hash check;
- every command actually run, exit status, collected/passed count, elapsed time, material
  output, and exact stop point if applicable;
- all before/after lock, ledger, raw-tree, amendment-ledger, and report identities;
- actual candidate exit, report SHA-256/bytes, gate state, acceptance, and blockers;
- candidate version/state, prior version/history/digests, content/envelope digests, input
  identities, plan entry/blocked/new/retained counts and bytes, and allowance;
- manifest selected/pending/consumable/collision/rejection and per-family counts;
- selected raw, cost sample, projected new, largest object, available space, unknown later
  storage components, and total-sufficiency state;
- membership and unresolved identities/classes, Coinalyze mapping/gaps, taker-flow evidence,
  holdout boundary, listing/retry evidence, and sample count; and
- an explicit statement that no plan/ledger migration, sample download, amendment-ledger
  creation, Gate 2, normalization, catalog publication, or model work occurred.

Hermes then changes both control files to
`Lead Quantitative Finance Researcher/Engineer - inspect review-110 candidate execution`,
adds record 110 to the governing documents, and leaves next ticket `NONE`. It stages and
commits exactly:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json` only if the candidate
  process ran;
- `research/sprint_004/110_CEX002_PLAN3_CANDIDATE_EXECUTION.md`; and
- `tickets/CEX-002.md`.

It pushes, establishes `HEAD == origin/main`, and stops for reviewer inspection.

## Disposition

CEX-002 remains `IN_PROGRESS`. Gate 1 has not passed. Plan-3 mutation, sample acquisition,
Gate 2, normalization, catalog publication, Nautilus work, Harmonic Trader work, payoff
analysis, PAPER, LIVE, and every other ticket remain unauthorized. Next ticket remains
`NONE`.
