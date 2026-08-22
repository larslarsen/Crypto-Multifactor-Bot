# CEX-002 ADR-0020 Source Acceptance

Date: 2026-08-21

Reviewer: Lead Quantitative Finance Researcher/Engineer

Reviewed head: `ad0a689c6a390ac5157bfd1a596c6277e50afa7c`

Governing review: `research/sprint_004/139_CEX002_CLAUDE_ADR0020_CORRECTION_REVIEW.md`

## Accepted source identities

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `2f9647d8c41dd69e3fce79889d889b54beb3c8742d8d7ef24d57803cdd2443b1` |
| `scripts/research/qualify_binance_usdm_harmonic_sources.py` | `8c455659af3a4ac13184b2ba4034dbeb1308a78e0834a2eed970159d6e577cbc` |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `3836413a2e667449e700b65477e10f2b30358f2099f1965d51f21bece9b4f248` |

The CEX test source contains 261 uniquely named `test_` functions. Frozen dependency
identities remain:

| Path | SHA-256 |
|---|---|
| `src/source_audit/download.py` | `f231930f743f4b2f415dd84a96ec3c1ec3b1c1efab5deb7536db57fce5473fa5` |
| `tests/test_download_atomicity.py` | `30388dba0568912b7bbe3f83c5454de89cd8cf5cd1288f260d30cfda0bd8d587` |

The existing CEX fixture directory remains frozen and unmodified.

The accepted pre-candidate compact report is 17,349,108 bytes at SHA-256
`e51ef2735c4937cf61cc614836478ee053c89f8100d5e4193a22e665f651fcd9`. Its already
preserved predecessor monolith remains 1,059,297,547 bytes at SHA-256
`46d1980ecf384874e45c4c31f142c16efc5472ef63231e9456e264f3e94ef691`.

## Decision

**ACCEPT THE COMPLETE ADR-0020 SOURCE/TEST/CLI DROP FOR HERMES INTEGRATION, FOCUSED
COMMANDS, AND ONE VERSION-4 CANDIDATE-ONLY EXECUTION.**

Review 139's four residuals are closed. Cost qualification now requires exactly one CSV
member, parses it through the standard strict CSV reader, preserves empty cells, and
normalizes CSV failures into the source-qualification error contract. Version-4 candidate
construction requires one lowercase 64-hex complete-cost-manifest identity. The retained-
content test reaches the intended content-rehash branch, and the complete source diff is
whitespace-clean.

Source inspection also accepts the review-138 correction: independent frozen-table counts
and digests; full literal authority tests; finite and provenance-bound delivery responses;
row/time/economic cost validation on fresh, reuse, and recovery paths; the versioned full
Gate-2 cost-manifest digest and candidate binding; non-cost-first qualification priority;
the six-object three-era cost sample; exact version-3 lineage; and all version-4 no-mutation
flags. Runtime evidence remains Hermes's responsibility.

## Hermes integration

Jr Dev - Hermes first establishes `HEAD == origin/main` at this review-publication commit.
It rehashes the three accepted paths and both frozen dependencies, proves the fixture
directory has no worktree diff, and re-proves the current compact report's exact hash and
size. A mismatch stops before staging.

Hermes stages exactly the three accepted Python paths, commits and pushes one implementation
integration commit, proves `HEAD == origin/main`, and proves the index is empty. It stages
no report, review, control, fixture, ignored data, database sidecar, or unrelated dirty
path. It uses no `git reset`, `git restore`, `git checkout`, `git stash`, `git clean`, or
equivalent worktree rewrite.

## Stop-on-first-failure commands

Only after the integration commit is pushed, Hermes runs these commands in order and stops
at the first nonzero exit:

1. `.venv/bin/python -m pytest tests/acquisition/test_binance_usdm_harmonic_qualification.py -q --tb=short`
2. `.venv/bin/python -m pytest tests/test_download_atomicity.py -q --tb=short`
3. `.venv/bin/python -m ruff check src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py scripts/research/qualify_binance_usdm_harmonic_sources.py src/source_audit/download.py tests/acquisition/test_binance_usdm_harmonic_qualification.py tests/test_download_atomicity.py`
4. `python3 scripts/check_repo_control.py`
5. `git show --check --oneline --no-renames HEAD`

Hermes records actual collected/pass counts. A failure prevents every later command and the
candidate.

## Preserve the current accepted report

Only after all five commands pass, Hermes atomically preserves the current compact report
at:

`data/cex002_qualify/evidence/prior_reports/sha256/e51ef2735c4937cf61cc614836478ee053c89f8100d5e4193a22e665f651fcd9.json`

The source must first re-prove at exactly 17,349,108 bytes and the accepted SHA-256. An
existing destination must already match. Otherwise Hermes copies to a collision-safe
sibling temporary file, never a hard link, rehashes and measures it, atomically renames it,
and re-proves the final destination. The preserved compact report and earlier monolith are
ignored evidence and are never staged.

## Candidate preconditions and one execution

Hermes proves no candidate process is running and captures a before snapshot of `HEAD`,
the empty index, plan lock, legacy ledger, amendment-ledger absence, retained raw tree,
listing checkpoint, retry journal, progress, caches, report, both preserved prior reports,
manifest-detail root, and available bytes. The locked version-2 authority, legacy ledger,
raw tree, 40,771-entry/zero-unclaimed listing state, current compact report, and preserved
monolith must match accepted evidence. An unexplained mismatch stops before launch.

Hermes loads `.env` only into the process environment and invokes exactly once in the
foreground:

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
Status 0 or 2 is terminal evidence, 124 is incomplete, and any other status is failure.
Every status stops after this one invocation; no automatic resume or second candidate is
authorized.

## Required after proof

Hermes captures the same snapshot and exact deltas. Any replaced receipt/detail must pass
the accepted ADR-0019 compactness, content-address, schema, digest, count, aggregate,
pending, phase-order, uniqueness, and reader-validation contracts. It must separately
prove and record:

- both authority-table hashes/counts and all 46 delivery plus 17 alias classifications;
- exactly three redacted delivery-pair response identities and no secret-bearing request;
- complete cost-manifest objects/bytes/gaps/versioned digest unchanged in scope and charged
  only to Gate 2;
- the six-object cost-source selector, non-cost-first priority, and unchanged
  268,435,456-byte Gate-1 allowance; validation summaries remain explicitly pending because
  candidate-only mode keeps samples empty;
- candidate version 4, the exact two superseded version-3 digests, prior versions 0-2,
  complete-cost digest/envelope binding, `migration_authorized=false`,
  `download_authorized=false`, and empty samples; and
- unchanged plan lock, legacy ledger, amendment-ledger absence, and retained raw tree.

No terminal status, report replacement, resolved membership, or valid candidate means Gate
1 passed or authorizes migration/download.

## Record and publication

Hermes writes `research/sprint_004/141_CEX002_ADR0020_INTEGRATION_AND_CANDIDATE.md` with
the exact integration commit, all command results or stop point, preservation proof,
before/after snapshots, candidate status, report/detail and ADR-0020 proofs, mutations, and
deviations.

After a valid terminal status-0/2 replacement, Hermes stages exactly:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json`;
- `research/sprint_004/141_CEX002_ADR0020_INTEGRATION_AND_CANDIDATE.md`; and
- `tickets/CEX-002.md`.

It changes both controls to `Next required actor: Lead Quantitative Finance
Researcher/Engineer - inspect record 141`, commits, pushes, proves `HEAD == origin/main`,
and stops. The two preserved prior reports and manifest detail are never staged.

On command, preservation, precondition, candidate, or validation failure, Hermes publishes
only the two matching controls and record 141 when safely possible and never stages an
invalid, oversized, or unchanged report. No retry or second candidate is authorized.

## Boundaries

No source/test edit after integration, plan migration, sample acquisition, Gate 2,
normalization, catalog publication, Nautilus work, Harmonic Trader work, payoff analysis,
PAPER, LIVE, paid source, Git LFS, external artifact service, scope reduction, report
truncation, unrelated-ticket work, or unrelated dirty-path mutation is authorized.

## Reviewer publication

The reviewer publishes exactly:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/140_CEX002_ADR0020_SOURCE_ACCEPTANCE.md`; and
- `tickets/CEX-002.md`.

The accepted source/test/CLI drop, reports, fixtures, ignored data, checkpoints, caches,
journals, database sidecars, and unrelated dirty paths are excluded.

## Disposition

CEX-002 remains `IN_PROGRESS`. Gate 1 has not passed. Next ticket remains `NONE`.
