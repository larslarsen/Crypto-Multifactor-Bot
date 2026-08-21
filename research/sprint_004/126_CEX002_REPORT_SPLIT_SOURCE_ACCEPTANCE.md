# CEX-002 Report Split Source Acceptance

Date: 2026-08-21

Reviewer: Lead Quantitative Finance Researcher/Engineer

Reviewed base: `2f893ab713cb7b07801810be031731833f9b4249`

Governing review: `research/sprint_004/125_CEX002_GROK_REPORT_SPLIT_RESIDUAL_REVIEW.md`

Accepted hashes:

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `6ef5c10c4ee9a5f7b19eb6ff711f73fa71eab792e3b9f393c8ae98d7b9504c8d` |
| `scripts/research/qualify_binance_usdm_harmonic_sources.py` | `b4e9235406be5276619b4a69017ddb87a8cffefb691c2673f2e3b875cc775d96` |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `7d046ce36d0912b728de7571cf49a227eda63191cb94fc9096f34b8fe5f67537` |

The CEX test source contains 209 uniquely named test functions. The accepted unchanged
atomic dependency hashes are:

| Path | SHA-256 |
|---|---|
| `src/source_audit/download.py` | `f231930f743f4b2f415dd84a96ec3c1ec3b1c1efab5deb7536db57fce5473fa5` |
| `tests/test_download_atomicity.py` | `30388dba0568912b7bbe3f83c5454de89cd8cf5cd1288f260d30cfda0bd8d587` |

All 17 CEX fixture files remain present. The oversized report remains byte-preserved at
SHA-256 `46d1980ecf384874e45c4c31f142c16efc5472ef63231e9456e264f3e94ef691`
and 1,059,297,547 bytes. The reviewer ran no pytest, Ruff, repository-control, network,
data, candidate, migration, or acceptance command.

## Decision

**ACCEPT THE COMPLETE ADR-0019 SOURCE/TEST DROP FOR HERMES INTEGRATION AND ONE CORRECTED
CANDIDATE-ONLY PUBLICATION.**

The final residual is closed. Manifest construction establishes deterministic key-primary
row order exactly once. The physical-object key is therefore both the order and uniqueness
identity, letting the validator reject adjacent duplicates and descending order while
retaining only `last_key`. Pending reconciliation remains two fixed-size rolling digests;
row counts, byte totals, consumable totals, and fixed-family counts remain recomputed from
the stream. No row-population-sized set, list, tuple, sort, database, or approximate filter
exists in validation.

The accepted drop also preserves the previously reviewed complete prevalidation,
compressed and uncompressed identities, strict schema/format/header and canonical path,
canonical JSONL, row-derived authority, atomic detail/receipt publication, failure cleanup,
bounded writer, compact receipt, and unchanged Gate-1 semantics. Source review finds no
remaining blocker. Runtime evidence remains Hermes's responsibility.

## Hermes integration authority

Jr Dev - Hermes must first establish `HEAD == origin/main` at this review-publication
commit and rehash every accepted/frozen path above. It must also prove the report's exact
pre-integration hash and size. A mismatch stops before staging.

Hermes stages exactly the three accepted source/test paths and commits and pushes them as
one implementation integration. It must not stage the oversized report, this review's
governance paths, database sidecars, data, or any unrelated dirty DEX, BitMEX, catalog,
ingest, config, or research path. It must not use `git reset`, `git restore`, `git checkout`,
`git stash`, `git clean`, or any equivalent worktree-rewriting command. After the
integration commit, it proves `HEAD == origin/main` and no path remains staged.

## Stop-on-first-failure commands

Only after the integration commit is pushed, Hermes runs these commands in order and stops
at the first nonzero exit:

1. `.venv/bin/python -m pytest tests/acquisition/test_binance_usdm_harmonic_qualification.py -q --tb=short`
2. `.venv/bin/python -m pytest tests/test_download_atomicity.py -q --tb=short`
3. `.venv/bin/python -m ruff check src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py scripts/research/qualify_binance_usdm_harmonic_sources.py src/source_audit/download.py tests/acquisition/test_binance_usdm_harmonic_qualification.py tests/test_download_atomicity.py`
4. `python3 scripts/check_repo_control.py`
5. `git show --check --oneline --no-renames HEAD`

Hermes records the exact collected/pass counts rather than inferring them from the 209
unique function definitions. Commands after a failure are not run, and no candidate is
started.

## Preserve the terminal monolith

After all five commands pass and before anything may replace report 62, Hermes publishes
its current exact bytes atomically at:

`data/cex002_qualify/evidence/prior_reports/sha256/46d1980ecf384874e45c4c31f142c16efc5472ef63231e9456e264f3e94ef691.json`

Hermes first rehashes the source report and requires both the accepted digest and
1,059,297,547-byte size. If the destination exists, its hash and size must already match.
Otherwise Hermes copies the source to a collision-safe sibling temporary file, preferably
with a filesystem reflink, rehashes and measures that temporary file, atomically renames it
to the content address, and rehashes the final destination. A mismatch or partial copy
stops before the candidate. The preserved artifact remains ignored local evidence and is
never staged. A hard link is not an acceptable preservation copy.

## Candidate preconditions

Hermes proves no candidate process is running and captures a before snapshot containing:

- `HEAD` and `origin/main` equality and an empty index;
- plan-lock, legacy-budget-ledger, amendment-ledger absence, retained-raw-tree, listing-
  checkpoint, retry-journal, progress, and cache hashes/counts/bytes;
- current report and preserved-prior-report hashes/counts/bytes;
- the preexisting manifest-detail-root file inventory, if any; and
- available filesystem bytes.

The plan lock, legacy ledger, amendment-ledger absence, and retained raw tree must match the
accepted record-121/review-122 terminal state. The completed listing checkpoint must have
40,771 entries and zero unclaimed requests. An unexplained mismatch stops before launch.

## One corrected candidate-only execution

Hermes loads `.env` only into the process environment, never prints a secret or places one
in an argument, and invokes exactly once in the foreground:

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
Status 0 or 2 is terminal evidence. Status 124 is an incomplete bounded slice. Any other
status is a failure. Every status stops after the one invocation for reviewer inspection;
no automatic resume or second invocation is authorized.

## Required after proof

Hermes captures the same snapshot after the process and records exact deltas. For a report
that the corrected writer successfully replaced, it must additionally prove:

- the tracked receipt is valid JSON, is below 90,000,000 bytes, and contains none of
  `rows`, `collisions`, `rejections`, or `raw_validation_pending_keys` on either receipt
  surface;
- its descriptor's relative path is the exact uncompressed SHA-256 content address under
  `evidence/manifests/sha256/`;
- compressed and uncompressed hashes/sizes, schema/format/header, every record count,
  object/byte/consumable totals, family totals, cadence, integrity, pending sequence, order,
  and uniqueness pass `validate_manifest_detail` through the accepted reader;
- the detail contains exactly 733,203 row records and no detailed collection was sampled,
  truncated, or staged; and
- the preserved prior report still has its accepted hash and size.

The record must separately state gate status, blockers, membership counts, candidate-plan
state and identities, `migration_authorized`, `download_authorized`, sample count, storage
state, listing reuse/fetch/serialization metrics, pooled-client counts, retries, and every
data/control mutation. No `accepted=true` or Gate-1 success claim follows merely from
successful evidence publication.

## Record and publication

Hermes writes
`research/sprint_004/127_CEX002_REPORT_SPLIT_INTEGRATION_AND_CANDIDATE.md` with the exact
integration commit, commands, outputs, before/after evidence, preservation proof,
candidate status, report/detail validation, and deviations.

After a valid terminal status-0/2 report replacement, Hermes stages exactly:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json`;
- `research/sprint_004/127_CEX002_REPORT_SPLIT_INTEGRATION_AND_CANDIDATE.md`; and
- `tickets/CEX-002.md`.

It changes the controls to `Next required actor: Lead Quantitative Finance
Researcher/Engineer - inspect review 127`, commits, pushes, proves `HEAD == origin/main`,
and stops. The ignored prior report and manifest detail are not staged. On a command
failure, candidate failure, timeout, invalid report/detail, or preservation failure,
Hermes publishes only the two controls and record 127 when safely possible; it must not
stage an invalid, oversized, or unchanged report.

## Boundaries

No plan migration, sample acquisition, Gate 2, normalization, catalog publication,
Nautilus work, Harmonic Trader work, payoff analysis, PAPER, LIVE, paid source, Git LFS,
external artifact service, scope reduction, report truncation, unrelated-ticket work, or
automatic second candidate invocation is authorized. No unrelated dirty path may be
staged, edited, reverted, moved, deleted, or cleaned.

## Reviewer publication

The reviewer publishes exactly:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/126_CEX002_REPORT_SPLIT_SOURCE_ACCEPTANCE.md`; and
- `tickets/CEX-002.md`.

The source/test drop, oversized report, ignored data, checkpoints, caches, journals,
database sidecars, and unrelated dirty paths are excluded.

## Disposition

CEX-002 remains `IN_PROGRESS`. Gate 1 has not passed. Next ticket remains `NONE`.
