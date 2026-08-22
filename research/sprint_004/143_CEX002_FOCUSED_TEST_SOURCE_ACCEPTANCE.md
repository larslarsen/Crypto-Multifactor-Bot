# CEX-002 Focused Test Source Acceptance

Date: 2026-08-21

Reviewer: Lead Quantitative Finance Researcher/Engineer

Reviewed head: `478c9306b1f17da2a840291e8efc679d9d9690e9`

Governing review: `research/sprint_004/142_CEX002_FOCUSED_TEST_FAILURE_REVIEW.md`

## Accepted source identities

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `2f9647d8c41dd69e3fce79889d889b54beb3c8742d8d7ef24d57803cdd2443b1` |
| `scripts/research/qualify_binance_usdm_harmonic_sources.py` | `8c455659af3a4ac13184b2ba4034dbeb1308a78e0834a2eed970159d6e577cbc` |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `186eccc22df2eb8f49f8f004141b6be7efdae15080afefa0675cfbd26e7a3fdd` |
| `src/source_audit/download.py` | `f231930f743f4b2f415dd84a96ec3c1ec3b1c1efab5deb7536db57fce5473fa5` |
| `tests/test_download_atomicity.py` | `30388dba0568912b7bbe3f83c5454de89cd8cf5cd1288f260d30cfda0bd8d587` |

The CEX test source contains exactly 261 uniquely named `test_` functions. The fixture
directory has no worktree change. The accepted pre-candidate compact report remains
17,349,108 bytes at SHA-256
`e51ef2735c4937cf61cc614836478ee053c89f8100d5e4193a22e665f651fcd9`.

## Decision

**ACCEPT THE EXACT ONE-ASSERTION TEST CORRECTION FOR HERMES INTEGRATION, A FULL FOCUSED-
COMMAND RESTART, AND THE PREVIOUSLY AUTHORIZED SINGLE CANDIDATE-ONLY EXECUTION.**

The complete worktree diff in the accepted test path changes only the expected archive
family count from 2 to 3 inside
`test_frozen_delivery_identity_resolves_only_while_its_evidence_reproves`. This matches the
three official families constructed by the fixture and leaves the two-family production
minimum unchanged. `git diff --check` is clean for the test path. No runtime result is
inferred from reviewer source inspection.

## Hermes integration

Jr Dev - Hermes first establishes `HEAD == origin/main` at this review-publication commit.
It rehashes all five accepted paths above, proves the fixture directory has no worktree
diff, and re-proves the current compact report's exact hash and size. A mismatch stops
before staging.

Hermes stages exactly
`tests/acquisition/test_binance_usdm_harmonic_qualification.py`, commits and pushes one
focused test-integration commit, proves `HEAD == origin/main`, and proves the index is
empty. It stages no control, review, report, fixture, ignored data, database sidecar, or
unrelated dirty path in that commit. It uses no `git reset`, `git restore`, `git checkout`,
`git stash`, `git clean`, or equivalent worktree rewrite.

## Stop-on-first-failure commands

Only after the focused test-integration commit is pushed, Hermes runs these commands in
order and stops at the first nonzero exit:

1. `.venv/bin/python -m pytest tests/acquisition/test_binance_usdm_harmonic_qualification.py -q --tb=short`
2. `.venv/bin/python -m pytest tests/test_download_atomicity.py -q --tb=short`
3. `.venv/bin/python -m ruff check src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py scripts/research/qualify_binance_usdm_harmonic_sources.py src/source_audit/download.py tests/acquisition/test_binance_usdm_harmonic_qualification.py tests/test_download_atomicity.py`
4. `python3 scripts/check_repo_control.py`
5. `git show --check --oneline --no-renames HEAD`

Hermes records actual collected/pass counts. A failure prevents every later command,
report preservation, and candidate work.

## Report preservation and candidate

Only after all five commands pass, Hermes performs review 140's report-preservation,
candidate-precondition, one-execution, and required-after-proof procedure without relaxing
or substituting any invariant. It first re-proves and atomically preserves the current
compact report at:

`data/cex002_qualify/evidence/prior_reports/sha256/e51ef2735c4937cf61cc614836478ee053c89f8100d5e4193a22e665f651fcd9.json`

The source report must be exactly 17,349,108 bytes with the accepted digest. An existing
destination must already match. A new copy uses a collision-safe sibling temporary file,
never a hard link, followed by rehash, atomic rename, and final reproof. This ignored
evidence is never staged.

Hermes proves no candidate process is running and captures review 140's complete before
snapshot. Every locked-authority, legacy-ledger, raw-tree, listing-state, compact-report,
preserved-monolith, manifest-detail, and available-byte precondition in review 140 remains
mandatory. An unexplained mismatch stops before launch.

Hermes then loads `.env` only into the process environment and makes exactly one foreground
invocation:

```bash
set -a
. ./.env
set +a
timeout --signal=TERM --kill-after=60s 50m \
  .venv/bin/python scripts/research/qualify_binance_usdm_harmonic_sources.py \
    --store-root data/cex002_qualify \
    --progress-path data/cex002_qualify/cex002_qualification_progress.json \
    --report-path research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json \
    --candidate-plan-only
candidate_status=$?
```

Hermes captures start/end timestamps, elapsed seconds, and `candidate_status` immediately.
Status 0 or 2 is terminal evidence, 124 is incomplete, and every other status is failure.
Every status stops after this invocation; no automatic resume or second candidate is
authorized.

Hermes then performs every required-after-proof check in review 140, including the exact
authority-table, delivery-response, complete-cost-manifest, six-object cost-source,
allowance, candidate-version/lineage, plan-lock, ledger, and retained-raw-tree proofs.
Candidate-only mode must keep samples empty and validation summaries explicitly pending.
No terminal status, report replacement, resolved membership, or valid candidate means Gate
1 passed or authorizes migration or download.

## Record and publication

Hermes writes
`research/sprint_004/144_CEX002_FOCUSED_TEST_INTEGRATION_AND_CANDIDATE.md` with the exact
test-integration commit, every command result or stop point, report-preservation proof,
before/after snapshots, candidate status, all review-140 post-proofs, mutations, and
deviations.

After a valid terminal status-0/2 report replacement, Hermes stages exactly:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json`;
- `research/sprint_004/144_CEX002_FOCUSED_TEST_INTEGRATION_AND_CANDIDATE.md`; and
- `tickets/CEX-002.md`.

It changes both controls to `Next required actor: Lead Quantitative Finance
Researcher/Engineer - inspect record 144`, commits, pushes, proves `HEAD == origin/main`,
and stops. Preserved reports and manifest detail are never staged.

On command, preservation, precondition, status-124, candidate, or validation failure,
Hermes publishes only the two matching controls and record 144 when safely possible and
never stages an invalid, oversized, or unchanged report. There is no retry or second
candidate.

## Boundaries

No source/test edit after integration, plan migration, sample acquisition, Gate 2,
normalization, catalog publication, Nautilus work, Harmonic Trader work, payoff analysis,
PAPER, LIVE, paid source, Git LFS, external artifact service, scope reduction, report
truncation, unrelated-ticket work, or unrelated dirty-path mutation is authorized.

## Reviewer publication

The reviewer publishes exactly:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/143_CEX002_FOCUSED_TEST_SOURCE_ACCEPTANCE.md`; and
- `tickets/CEX-002.md`.

The accepted test drop, report, fixture, ignored data, checkpoint, cache, journal, database
sidecar, and unrelated dirty paths are excluded. The reviewer executes no pytest, Ruff,
repository-control, candidate, migration, sample, or data-mutating command.

## Disposition

CEX-002 remains `IN_PROGRESS`. Gate 1 has not passed. Next ticket remains `NONE`.
