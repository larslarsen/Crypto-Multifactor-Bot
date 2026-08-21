# CEX-002 Spark Test Source Acceptance

Date: 2026-08-21

Reviewer: Lead Quantitative Finance Researcher/Engineer

Reviewed head: `0ce86821f7ddb625594e2f3226366f7c883ee7f3`

Governing review: `research/sprint_004/129_CEX002_SPARK_TEST_SOURCE_REVIEW.md`

Accepted test hash:

| Path | SHA-256 |
|---|---|
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `23f1159f8d664f0c55b26498ef69ea72196bb70279055ccf6f9da06dea0d550b` |

The test source contains 209 uniquely named test functions. Frozen integrated hashes:

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `6ef5c10c4ee9a5f7b19eb6ff711f73fa71eab792e3b9f393c8ae98d7b9504c8d` |
| `scripts/research/qualify_binance_usdm_harmonic_sources.py` | `b4e9235406be5276619b4a69017ddb87a8cffefb691c2673f2e3b875cc775d96` |
| `src/source_audit/download.py` | `f231930f743f4b2f415dd84a96ec3c1ec3b1c1efab5deb7536db57fce5473fa5` |
| `tests/test_download_atomicity.py` | `30388dba0568912b7bbe3f83c5454de89cd8cf5cd1288f260d30cfda0bd8d587` |

The 17 CEX fixtures remain frozen. The on-disk monolith remains exactly 1,059,297,547
bytes at SHA-256
`46d1980ecf384874e45c4c31f142c16efc5472ef63231e9456e264f3e94ef691`.
It has not yet been copied to the prior-report content address. The reviewer ran no pytest,
Ruff, repository-control, network, data, candidate, migration, or acceptance command.

## Decision

**ACCEPT THE SINGLE TEST PATH FOR HERMES INTEGRATION AND REAUTHORIZE THE COMPLETE CORRECTED
CANDIDATE PUBLICATION SEQUENCE.**

Spark's accepted first correction proves the storage acquisition-manifest surface contains
none of the four detailed collections and reconciles all counts, rules, family totals, and
detail identity with the sole top-level manifest authority. The residual correction now
compact-serializes the parsed receipt and every complete selected row identically, proves
no complete 13-field row object occurs anywhere in the receipt, proves a nonempty selected-
key/sample-plan-key intersection, and proves those legitimate plan references remain
serialized. Review 128's two test defects are closed without changing a test function or
production behavior.

## Hermes test integration

Jr Dev - Hermes first establishes `HEAD == origin/main` at this review-publication commit
and rehashes the accepted test plus all four frozen paths above, the 17 fixtures, and the
monolith. A mismatch stops before staging.

Hermes stages exactly
`tests/acquisition/test_binance_usdm_harmonic_qualification.py`, commits and pushes one
test-integration commit, proves `HEAD == origin/main`, and proves the index is empty. It
must not stage the monolith, ignored data, controls, records, database sidecars, or any
unrelated dirty path. It must not use `git reset`, `git restore`, `git checkout`, `git
stash`, `git clean`, or any equivalent worktree rewrite.

## Restart all focused commands

Hermes restarts, in order, the complete stop-on-first-failure sequence from review 126:

1. `.venv/bin/python -m pytest tests/acquisition/test_binance_usdm_harmonic_qualification.py -q --tb=short`
2. `.venv/bin/python -m pytest tests/test_download_atomicity.py -q --tb=short`
3. `.venv/bin/python -m ruff check src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py scripts/research/qualify_binance_usdm_harmonic_sources.py src/source_audit/download.py tests/acquisition/test_binance_usdm_harmonic_qualification.py tests/test_download_atomicity.py`
4. `python3 scripts/check_repo_control.py`
5. `git show --check --oneline --no-renames HEAD`

Hermes records actual collected/pass counts. It does not assume a collected count from the
209 unique function definitions. Any nonzero exit stops the remaining commands and the
candidate.

## Preservation, snapshot, and one candidate

Only after all five commands pass, Hermes executes review 126's complete sections
`Preserve the terminal monolith`, `Candidate preconditions`, `One corrected candidate-only
execution`, and `Required after proof` without alteration. In particular:

- the current report must first be atomically copied, never hard-linked, to
  `data/cex002_qualify/evidence/prior_reports/sha256/46d1980ecf384874e45c4c31f142c16efc5472ef63231e9456e264f3e94ef691.json`
  and re-proved at the accepted hash and 1,059,297,547-byte size;
- the full before snapshot and the completed 40,771-entry/zero-unclaimed listing state
  must pass before launch;
- `.env` is loaded only into the environment and the exact review-126 foreground command
  runs once under `timeout --signal=TERM --kill-after=60s 50m` with
  `--candidate-plan-only`;
- status 0 or 2 is terminal evidence, 124 is an incomplete slice, and any other status is
  failure; every status stops with no automatic second invocation; and
- a replaced receipt/detail must pass every review-126 compactness, content-address,
  reader-validation, 733,203-row, aggregate, pending, order, uniqueness, preservation, and
  unchanged-authority proof before publication.

No status or successful evidence write by itself means Gate 1 passed.

## Record and publication

Hermes writes
`research/sprint_004/131_CEX002_TEST_INTEGRATION_AND_CANDIDATE.md` with the exact test-
integration commit, all five command results or stop point, preservation proof, before and
after snapshots, candidate status, report/detail proof, exact mutations, and deviations.

After a valid terminal status-0/2 replacement, Hermes stages exactly:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json`;
- `research/sprint_004/131_CEX002_TEST_INTEGRATION_AND_CANDIDATE.md`; and
- `tickets/CEX-002.md`.

It changes the controls to `Next required actor: Lead Quantitative Finance
Researcher/Engineer - inspect record 131`, commits, pushes, proves `HEAD == origin/main`,
and stops. The ignored prior report and manifest detail are not staged.

On a command, preservation, precondition, candidate, or validation failure, Hermes
publishes only the two controls and record 131 when safely possible and never stages an
invalid, oversized, or unchanged report. No automatic retry or second candidate run is
authorized.

## Boundaries

No production/test edit, plan migration, sample acquisition, Gate 2, normalization,
catalog publication, Nautilus work, Harmonic Trader work, payoff analysis, PAPER, LIVE,
paid source, Git LFS, external artifact service, scope reduction, report truncation,
unrelated-ticket work, or unrelated dirty-path mutation is authorized after the exact test
integration. Every unrelated dirty path remains untouched and unstaged.

## Reviewer publication

The reviewer publishes exactly:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/130_CEX002_SPARK_TEST_SOURCE_ACCEPTANCE.md`; and
- `tickets/CEX-002.md`.

The accepted test drop, monolith, ignored data, checkpoints, caches, journals, database
sidecars, and unrelated dirty paths are excluded.

## Disposition

CEX-002 remains `IN_PROGRESS`. Gate 1 has not passed. Next ticket remains `NONE`.
