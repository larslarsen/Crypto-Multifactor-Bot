# CEX-002 Ruff Source Acceptance

Date: 2026-08-21

Reviewer: Lead Quantitative Finance Researcher/Engineer

Reviewed head: `ee70777ad21dfb1525c09f130f88e4a13b423f8b`

Governing review: `research/sprint_004/132_CEX002_RUFF_FAILURE_REVIEW.md`

Accepted hashes:

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `8b006ad3eebf059f9d3ce4f3e75b22192bff1272c693b1a69931a3936c571b99` |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `500882b5fc784722bab9e69038ee0d28fbe22c6d8558237a46607e354e0c9463` |

The CEX test source contains 209 uniquely named test functions. Frozen unchanged hashes:

| Path | SHA-256 |
|---|---|
| `scripts/research/qualify_binance_usdm_harmonic_sources.py` | `b4e9235406be5276619b4a69017ddb87a8cffefb691c2673f2e3b875cc775d96` |
| `src/source_audit/download.py` | `f231930f743f4b2f415dd84a96ec3c1ec3b1c1efab5deb7536db57fce5473fa5` |
| `tests/test_download_atomicity.py` | `30388dba0568912b7bbe3f83c5454de89cd8cf5cd1288f260d30cfda0bd8d587` |

The 17 fixtures remain frozen. The monolith remains exactly 1,059,297,547 bytes at
SHA-256 `46d1980ecf384874e45c4c31f142c16efc5472ef63231e9456e264f3e94ef691`
and has not yet been copied to the prior-report content address. The reviewer ran no
pytest, Ruff, repository-control, network, data, candidate, migration, or acceptance
command.

## Decision

**ACCEPT THE TWO MECHANICAL RUFF CORRECTIONS FOR HERMES INTEGRATION AND REAUTHORIZE THE
COMPLETE CORRECTED CANDIDATE PUBLICATION SEQUENCE.**

The production change renames only the local Coinalyze history tuple target from `fields`
to `point_fields` and passes the same tuple into `required_point_fields`; its necessary
line wrap changes no value or behavior. The test change deletes only the unused
`rendered = receipt_path.read_bytes()` assignment. No assertion, source authority,
financial semantic, network behavior, manifest identity, report contract, or test count
changed.

## Hermes integration

Jr Dev - Hermes first establishes `HEAD == origin/main` at this review-publication commit
and rehashes both accepted paths, all three frozen paths, all 17 fixtures, and the
monolith. A mismatch stops before staging.

Hermes stages exactly the two accepted paths, commits and pushes one mechanical
integration commit, proves `HEAD == origin/main`, and proves the index is empty. It stages
no monolith, ignored data, control, record, database sidecar, or unrelated dirty path and
uses no `git reset`, `git restore`, `git checkout`, `git stash`, `git clean`, or equivalent
worktree rewrite.

## Full command restart

Hermes runs all five commands from the beginning and stops at the first nonzero exit:

1. `.venv/bin/python -m pytest tests/acquisition/test_binance_usdm_harmonic_qualification.py -q --tb=short`
2. `.venv/bin/python -m pytest tests/test_download_atomicity.py -q --tb=short`
3. `.venv/bin/python -m ruff check src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py scripts/research/qualify_binance_usdm_harmonic_sources.py src/source_audit/download.py tests/acquisition/test_binance_usdm_harmonic_qualification.py tests/test_download_atomicity.py`
4. `python3 scripts/check_repo_control.py`
5. `git show --check --oneline --no-renames HEAD`

Hermes records actual collected/pass counts. Previous C1/C2 passes are positive evidence
but are not substituted for this restart. A failure prevents every later command and the
candidate.

## Preservation and one candidate

Only after all five commands pass, Hermes executes review 126's `Preserve the terminal
monolith`, `Candidate preconditions`, `One corrected candidate-only execution`, and
`Required after proof` sections exactly, as reaffirmed by reviews 130 and 133. This means:

- atomically copy, never hard-link, the monolith to
  `data/cex002_qualify/evidence/prior_reports/sha256/46d1980ecf384874e45c4c31f142c16efc5472ef63231e9456e264f3e94ef691.json`
  and re-prove its hash and 1,059,297,547-byte size before launch;
- prove the complete before snapshot, including the 40,771-entry/zero-unclaimed listing
  state and every immutable authority;
- load `.env` only into the environment and run the exact review-126 foreground
  `--candidate-plan-only` command once under the 50-minute timeout;
- treat status 0/2 as terminal evidence, 124 as an incomplete slice, and any other status
  as failure, with no automatic second invocation; and
- validate any replaced compact receipt and content-addressed detail through every
  review-126 size, schema, digest, count, 733,203-row, aggregate, pending, order,
  uniqueness, preservation, and unchanged-authority check.

No successful command, candidate status, or evidence write by itself means Gate 1 passed.

## Record and publication

Hermes writes
`research/sprint_004/134_CEX002_RUFF_INTEGRATION_AND_CANDIDATE.md` with the exact integration
commit, all command outputs or stop point, preservation, before/after snapshots, candidate
status, detail/receipt validation, mutations, and deviations.

After a valid terminal status-0/2 replacement, Hermes stages exactly:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json`;
- `research/sprint_004/134_CEX002_RUFF_INTEGRATION_AND_CANDIDATE.md`; and
- `tickets/CEX-002.md`.

It changes both controls to `Next required actor: Lead Quantitative Finance
Researcher/Engineer - inspect record 134`, commits, pushes, proves `HEAD == origin/main`,
and stops. The ignored prior report and manifest detail are not staged.

On a command, preservation, precondition, candidate, or validation failure, Hermes
publishes only the two matching controls and record 134 when safely possible, and never
stages an invalid, oversized, or unchanged report. No retry or second candidate is
authorized.

## Boundaries

No further source/test edit, plan migration, sample acquisition, Gate 2, normalization,
catalog publication, Nautilus work, Harmonic Trader work, payoff analysis, PAPER, LIVE,
paid source, Git LFS, external artifact service, scope reduction, report truncation,
unrelated-ticket work, or unrelated dirty-path mutation is authorized. Every unrelated
dirty path remains untouched and unstaged.

## Reviewer publication

The reviewer publishes exactly:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/133_CEX002_RUFF_SOURCE_ACCEPTANCE.md`; and
- `tickets/CEX-002.md`.

The accepted source/test drop, monolith, ignored data, checkpoints, caches, journals,
database sidecars, and unrelated dirty paths are excluded.

## Disposition

CEX-002 remains `IN_PROGRESS`. Gate 1 has not passed. Next ticket remains `NONE`.
