# CEX-002 Listing Source Acceptance

Date: 2026-08-21

Reviewer: Lead Quantitative Finance Researcher/Engineer

Reviewed base: `f987da574b3c24360d9cfbab82b282343ad1c9c0`

Subject review: `research/sprint_004/119_CEX002_LISTING_RESIDUAL_TEST_REVIEW.md`

Accepted hashes:

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `b6077bf833ae59b2414b441564764179fc0dcff0db6cec3457139a5a26df53e8` |
| `scripts/research/qualify_binance_usdm_harmonic_sources.py` | `45e0f6990df6a71d6197a6b981270ae63b79897553595e6a9b05f912ecfb3f63` |
| `src/source_audit/download.py` | `f231930f743f4b2f415dd84a96ec3c1ec3b1c1efab5deb7536db57fce5473fa5` |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `88b62427ffb125b509f150279f934a8c0bf151a62e985af070518c1d32f844c5` |
| `tests/test_download_atomicity.py` | `30388dba0568912b7bbe3f83c5454de89cd8cf5cd1288f260d30cfda0bd8d587` |

The CEX test source contains 186 uniquely named test functions. The atomic-download test
source contains 18 uniquely named test functions. The 17 CEX fixture files are unchanged.
The reviewer ran no pytest, Ruff, repository-control, network, data, candidate, or
migration command.

## Decision

**ACCEPT ALL FIVE PATHS FOR HERMES INTEGRATION AND FOCUSED EXECUTION. AFTER ALL
FOCUSED COMMANDS PASS, AUTHORIZE EXACTLY ONE MEASURED CANDIDATE RESUME SLICE.**

The corrected cleanup test now proves that an active qualification failure remains
primary while pool close and checkpoint flush are both attempted and the cleanup failure
is reported second. The concurrent retry proof now uses retryable `DownloadError`
instances, executes the shared runner and durable journal under controlled forward and
inverted completion order, proves two attempts per request, and proves canonical redacted
report and journal evidence. No test was removed, no production contract changed in the
last correction, and every review-119 frozen hash still matches.

The complete ADR-0018 implementation is therefore accepted statically. This is not test,
real-source, candidate-plan, or Gate-1 acceptance.

## Reviewer publication

The reviewer publishes exactly:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/120_CEX002_LISTING_SOURCE_ACCEPTANCE.md`; and
- `tickets/CEX-002.md`.

No source, test, fixture, data, report, checkpoint, cache, database sidecar, or unrelated
dirty path belongs to the reviewer publication.

## Hermes integration

Jr Dev - Hermes first establishes `HEAD == origin/main` at the review-120 publication
commit and verifies all five accepted hashes plus the unchanged 17-file fixture directory.
Hermes stages exactly the five accepted paths above, commits them as one forward source
integration, and excludes every unrelated dirty path, fixture, data file, report, control
file, database sidecar, cache, checkpoint, and journal.

No restore, reset, checkout, stash, clean, deletion, cache reset, store reconstruction,
relock, source edit, test edit, or fixture edit is authorized. Existing unrelated dirty
DEX, BitMEX, catalog, ingest, configuration, research, database-sidecar, and other-ticket
paths must be preserved and must not enter either commit.

## Focused commands

Hermes runs exactly these commands in order after the source-integration commit:

1. `.venv/bin/python -m pytest tests/acquisition/test_binance_usdm_harmonic_qualification.py -q --tb=short`
2. `.venv/bin/python -m pytest tests/test_download_atomicity.py -q --tb=short`
3. `.venv/bin/python -m ruff check src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py scripts/research/qualify_binance_usdm_harmonic_sources.py src/source_audit/download.py tests/acquisition/test_binance_usdm_harmonic_qualification.py tests/test_download_atomicity.py`
4. `python3 scripts/check_repo_control.py`
5. `git show --check --oneline --no-renames HEAD`

Command 1 must collect and pass 186 tests; command 2 must collect and pass 18. Any nonzero
exit or count mismatch stops the sequence immediately. Results after a failed predecessor
are void, and Hermes runs no candidate process. Hermes records the failure in record 121,
publishes the control transition described below, pushes, and stops for review.

The full repository suite remains deferred to final CEX-002 release acceptance because
unrelated dirty DEX/BitMEX work is outside this integration. No `-k` substitute,
clean-worktree reconstruction, unrelated test command, or discretionary rerun is
authorized.

## Candidate preconditions

Only after all five focused commands pass, Hermes proves no prior candidate process is
running and captures one timestamped before snapshot. It records:

- `HEAD`, `origin/main`, all five accepted hashes, and the 17-fixture tree identity;
- SHA-256 and bytes for the version-2 plan lock, legacy budget ledger, tracked report,
  listing checkpoint, retry journal, and qualification progress;
- a deterministic recursive path/size/content digest, file count, and bytes for the
  retained raw tree;
- amendment-ledger absence or, if unexpectedly present, its identity;
- listing-checkpoint entry and unclaimed counts plus latest retrieval time;
- deterministic path/size/content digests, file counts, and byte counts for `list_cache`,
  `fapi_cache`, and `coinalyze_cache`;
- filesystem available bytes; and
- the current terminal/stale state of the tracked report.

The plan lock, legacy ledger, tracked report, retained raw tree, and amendment-ledger
absence must match review 115's proved after state. Any mismatch, a changed accepted hash,
an unexplained listing-state change, or an already running candidate stops before launch
and is recorded. The existing checkpoint and caches must be reused in place.

## One measured candidate resume

Hermes loads the secret only from `.env` into the environment, never prints it, and never
places it in a command argument. It records start time and runs exactly one bounded
foreground invocation:

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

Hermes captures `candidate_status`, end time, and elapsed time immediately and does not
invoke the candidate again. Status 0 or 2 is terminal evidence for review. Status 124 is a
measured timeout, not success. Status 1 or any other status is a measured failure. No
status authorizes plan migration, sample acquisition, or Gate 2.

After every status, including 1, 124, or forced termination, Hermes repeats the complete
before snapshot. It records every execution-plane delta, including checkpoint
serialization/recovery counters when available, and proves the lock, ledger, raw tree,
amendment-ledger state, and tracked-report identity or change. A timeout records exact
checkpoint/cache progress and stops; a second invocation is not authorized.

For terminal status 0 or 2, record 121 also includes the report's gate and acceptance
state; blockers; complete candidate version/history/content/envelope/input identities;
plan entry, blocked, retained, new-object, byte, and allowance fields; manifest
selected/pending/consumable/collision/rejection and per-family counts; storage fields;
membership and unresolved classes; Coinalyze mapping/gaps; taker-flow evidence; holdout;
listing, pool, checkpoint, recovery, and retry evidence; empty `samples`; and explicit
`migration_authorized=false` and `download_authorized=false`.

## Record and publication

Hermes creates
`research/sprint_004/121_CEX002_LISTING_INTEGRATION_AND_CANDIDATE_RESUME.md`. It records
the integration commit, every hash check, every command actually run with exit/status,
test counts, elapsed time, material output, the exact stop point, the complete before/after
evidence, and an explicit statement that no migration, sample download, amendment-ledger
creation, Gate 2, normalization, catalog publication, Nautilus work, Harmonic Trader work,
payoff analysis, PAPER, LIVE, or other-ticket work occurred.

Hermes then changes both control files to `Lead Quantitative Finance
Researcher/Engineer - inspect review-121 integration and candidate resume`, adds record
121 to the governing documents, and leaves next ticket `NONE`. It stages and commits
exactly:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/121_CEX002_LISTING_INTEGRATION_AND_CANDIDATE_RESUME.md`;
- `tickets/CEX-002.md`; and
- `research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json` only if its bytes changed
  through the authorized candidate process.

Hermes pushes both commits, proves `HEAD == origin/main`, and stops. Data, checkpoint,
cache, progress, journal, database-sidecar, and unrelated dirty paths remain uncommitted.
Review 120 is the complete task; no owner-supplied chat instruction is authority.

## Disposition

CEX-002 remains `IN_PROGRESS`. Gate 1 has not passed. Plan migration, sample acquisition,
Gate 2, normalization, catalog publication, Nautilus work, Harmonic Trader work, payoff
analysis, PAPER, LIVE, and every other ticket remain unauthorized. Next ticket remains
`NONE`.
