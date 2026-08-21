# CEX-002 Focused Correction Source Acceptance

Date: 2026-08-20

Reviewer: Lead Quantitative Finance Researcher/Engineer

Reviewed base: `20e36fc081eb5343a9ded716299bfbe1eef869f0`

Accepted source/test hashes:

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `3453c1cfec2d3ee39d02eddf956e9a52438e101518bf5c6677a1f4d15a76071c` |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `4041f327f579eee773aa19d9345f325683916322cb5800b6461ec8b66e250ef2` |

Frozen CLI hash:
`7c60f4d5bd7eacf9f0b85bac4a5d356106d035a5613e2a4e38163697906822d8`

The 17 tracked fixture files remain unchanged. Static counting finds 170 uniquely named
test functions and no duplicate names.

## Decision

**ACCEPT THE REVIEW-105 CORRECTION FOR JR INTEGRATION AND RESTARTED FOCUSED EXECUTION.**

This is static source acceptance only. The reviewer ran no pytest, Ruff, repo-control,
acceptance, network, data, or migration command. The focused suite, real candidate report,
version-3 candidate, and Gate-1 evidence are not yet accepted.

## Accepted correction

The production module preserves the immutable locked plan and its execution order. After a
normal execution it rebuilds only the report-facing manifest and selected-storage evidence
from retained bytes re-proved at startup plus sample records whose object content and
provider sidecar were validated during the current invocation. A bare checkpoint claim is
not promoted. Candidate mode still executes no plan entries and can publish only re-proved
retained evidence. The acquisition manifest remains in semantic identity rather than being
masked as volatility.

Candidate taker flow continues to require native one-hour kline schema proof and no
trade/aggregate-trade fetch. When a re-proved retained schema contains all required fields,
the derived row replaces only the artificial zero-current-sample state with official or
typed-gap state. Its inherited release block is cleared only for complete or nonblocking
typed-gap coverage without a real sample-budget block. Blocking coverage, unresolved
membership, budget blocks, unavailable schema, and invalid schema remain visible and
blocking.

The test source now uses selected checksummed one-hour kline objects for tamper protection,
emits deterministic schema-valid distinct kline bytes for selected kline keys, expects
native-kline-derived taker-flow authority, tests family-launch behavior through actual
kline inputs, and checks exact CLI flags rather than banning explanatory text. Stable
identity, interrupted resume, no-refetch, transfer accounting, retained sidecar proof,
candidate zero-fetch, absent-schema blocking, exact prior authority, secret redaction, and
immutable lineage assertions remain in place. The retained-schema candidate test now also
requires both evidence and `release_blocked_derived` to be false for its nonblocking case.

## Control-plane correction

After Claude's first drop, the reviewer improperly sent a corrective clarification through
chat instead of first publishing it in the repository control plane. That chat message is
not treated as independent authorization. The final source remains within review 105's
already published two-path scope and its requirement to remove only the artificial
sample-pending condition while preserving real blocks. This review records the completed
interpretation and every next instruction. No later developer correction or execution is
authorized unless it first appears in the current task, ticket, and a governing review.

## Hermes integration

Jr Dev - Hermes first establishes that `HEAD == origin/main` at the review-106 publication
commit. It verifies the two accepted hashes, the frozen CLI hash, and the unchanged fixture
directory. It stages exactly the two accepted paths, commits them as a forward correction,
pushes, and re-establishes `HEAD == origin/main`.

No unrelated dirty path, fixture, data file, report, control file, or database sidecar
belongs to the source-integration commit. No restore, reset, checkout, stash, clean,
deletion, reconstruction, or relock is authorized.

## Focused commands

Hermes then runs these commands in order:

1. `.venv/bin/python -m pytest tests/acquisition/test_binance_usdm_harmonic_qualification.py -q --tb=short`
2. `.venv/bin/python -m pytest tests/test_download_atomicity.py -q --tb=short`
3. `.venv/bin/python -m ruff check src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py scripts/research/qualify_binance_usdm_harmonic_sources.py tests/acquisition/test_binance_usdm_harmonic_qualification.py`
4. `python3 scripts/check_repo_control.py`
5. `git show --check --oneline --no-renames HEAD`

Any nonzero exit stops immediately. Hermes must not run any subsequent command in the list
and must not run the real candidate process after a failure. It records the failure in
record 107 exactly as observed. The commands must be restarted from command 1 after any
later correction; results after a failed predecessor are not acceptance evidence.

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

The actual process status is captured immediately. Exit 1 stops and is not retried. Exit 0
or 2 permits evidence publication but is not migration, acquisition, Gate-1 acceptance, or
success by itself.

Hermes repeats every before-state measurement. The exact version-2 lock SHA, legacy-ledger
SHA, and raw-tree digest/count/bytes must match; the amendment ledger must remain absent;
`samples` must be empty; and the report must state `migration_authorized=false` and
`download_authorized=false`. Any mismatch is a failure and stops.

## Execution record

Hermes creates `research/sprint_004/107_CEX002_PLAN3_CANDIDATE_EXECUTION.md`. It records:

- the source-integration commit and every accepted/frozen hash check;
- every command actually run, its exit status, collected/passed count, elapsed time, and
  material output, with an explicit stop point if applicable;
- all before/after authority, raw-tree, amendment-ledger, and report identities;
- actual candidate process exit, report SHA-256/bytes, gate state, acceptance, and blockers;
- candidate version/state, prior version/history/digests, content/envelope digests, input
  identities, plan entry/blocked/new/retained counts and bytes, and allowance;
- acquisition-manifest selected/pending/consumable/collision/rejection and per-family
  counts;
- selected raw, cost sample, projected new, largest object, available space, unknown later
  storage components, and total-sufficiency state;
- membership, unresolved identities/classes, Coinalyze mapping/gaps, taker-flow evidence,
  holdout boundary, listing/retry evidence, and sample count; and
- an explicit statement that no plan/ledger migration, sample download, amendment-ledger
  creation, Gate 2, normalization, catalog publication, or model work occurred.

Hermes then changes both control files to
`Lead Quantitative Finance Researcher/Engineer - inspect review-107 candidate execution`,
adds record 107 to the governing documents, and leaves next ticket `NONE`. It stages and
commits exactly:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json` only if the candidate
  process ran;
- `research/sprint_004/107_CEX002_PLAN3_CANDIDATE_EXECUTION.md`; and
- `tickets/CEX-002.md`.

It pushes, establishes `HEAD == origin/main`, and stops for reviewer inspection.

## Disposition

CEX-002 remains `IN_PROGRESS`. Gate 1 has not passed. Plan-3 mutation, sample acquisition,
Gate 2, normalization, catalog publication, Nautilus work, Harmonic Trader work, payoff
analysis, PAPER, LIVE, and every other ticket remain unauthorized. Next ticket remains
`NONE`.
