# CEX-002 Candidate Timeout Review

Date: 2026-08-20

Reviewer: Lead Quantitative Finance Researcher/Engineer

Reviewed head: `3c8404f0290146a36078149fd6bcb420687f4712`

Subject record: `research/sprint_004/113_CEX002_PLAN3_CANDIDATE_EXECUTION.md`

## Decision

**ACCEPT THE SOURCE INTEGRATION AND FOCUSED COMMANDS. REJECT THE CANDIDATE
EXECUTION RECORD AS TERMINAL EVIDENCE. AUTHORIZE ONE MEASURED RESUME SLICE.**

Commit `2657f73` contains the exact review-112 production source. Record 113 reports a
strict, passing sequence of 189 CEX-002 tests, 11 atomic-download tests, Ruff, repository
control, and the committed-diff whitespace check. Those results are accepted. No source or
test correction and no repeat of those five commands is warranted on the unchanged source.

The real candidate invocation is not accepted as a completed execution. It has neither the
required before-state measurements nor a process exit status. The statement that no
mutation occurred is also false for the execution plane: the listing checkpoint and
content-addressed listing cache advanced during the invocation. Record 113 may remain as
an honest record of the incomplete attempt, but it is not Gate-1 or candidate evidence.

## Post-timeout inspection

The reviewer performed read-only, post-event inspection. Because Hermes omitted the
required before snapshot, these observations cannot reconstruct an exact before/after
delta and must not be represented as one.

| Evidence | Current state |
|---|---|
| version-2 plan lock SHA-256 | `e04a5ce2f2513cc8a0f4e6698dcbf9d43c5a7bec0295021ca5d431ff886f0d84` |
| legacy budget ledger SHA-256 | `47341a9ca2c60caf73485fb9bac40c6526cb35a13471e4545cd9cdcee6e227f6` |
| tracked report SHA-256 | `dce2a2396c6b250be928f4cde217ce49419561f958301ad97afbd479b6b39e31` |
| amendment ledger | absent |
| retained raw tree | 186 files; 1,015,198,547 bytes |
| listing checkpoint SHA-256 | `86c1aec9e0056a9f3fdc53295d18f32527d79f44e7193b3c0a1760b11bffc084` |
| listing checkpoint | 30,570 entries; 24,554,819 bytes |
| content-addressed listing cache | 30,759 files; 3,443,186,770 bytes |
| retry journal SHA-256 | `ab820dddceca958779b0b4d514fa48f58aa23de1923e0fde88314aa45922d404` |
| qualification progress SHA-256 | `332f2d87fd7499b2f0a54b532b450042feea25e0ac6e4f3f031f184f67125912` |
| local filesystem available at inspection | 182,006,964,224 bytes |

The checkpoint contains listing responses retrieved through the end of the interrupted
window, while the lock, legacy ledger, report, raw tree, and amendment-ledger absence retain
their prior identities. The last console line cited by record 113 was a bootstrap status,
not proof that the process remained at bootstrap for the full hour. The timeout therefore
shows resumable inventory progress, not a storage-capacity block and not yet a source-code
performance defect. The existing checkpoint and cache must be reused.

## Frozen implementation

Hermes first establishes `HEAD == origin/main` at the review-114 publication commit and
verifies these hashes:

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `85945a4bbfb89589ae350f7649504a01e66a9118dc0e158423aaf97447e2b517` |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `4ef66b0e527e890956075d7565601821eed7fab59307a11339d4e1afffb7e692` |
| `scripts/research/qualify_binance_usdm_harmonic_sources.py` | `7c60f4d5bd7eacf9f0b85bac4a5d356106d035a5613e2a4e38163697906822d8` |

No production, CLI, test, fixture, report, data, checkpoint, cache, journal, or progress
file may be edited manually. No restore, reset, checkout, stash, clean, deletion, cache
reset, store reconstruction, relock, test execution, or source integration is authorized.

## Required before snapshot

Before launching a process, Hermes proves that no prior candidate process is running and
captures one timestamped snapshot containing:

- `HEAD` and `origin/main`, the three frozen hashes above, and the 17-fixture tree identity;
- SHA-256 and bytes for the plan lock, legacy ledger, tracked report, listing checkpoint,
  retry journal, and qualification progress;
- a deterministic recursive path/size/content digest, file count, and byte count for the
  retained raw tree;
- amendment-ledger absence or its identity if unexpectedly present;
- listing-checkpoint entry and unclaimed counts plus its latest retrieval timestamp;
- a deterministic path/size manifest digest, file count, and bytes for `list_cache`, and
  equivalent count/byte/digest measurements for `fapi_cache` and `coinalyze_cache`;
- filesystem available bytes; and
- the exact existing report state needed to compare a terminal candidate result.

Any mismatch in the frozen implementation, lock, ledger, raw tree, amendment-ledger
absence, or current tracked report relative to this review stops before launch. Hermes
records the mismatch in record 115 and runs no candidate command.

## One measured resume slice

Only after the before snapshot passes, Hermes loads the secret from `.env` without printing
it and runs exactly one bounded foreground invocation against the existing store. The
50-minute boundary leaves time inside a one-hour agent window to capture evidence even if
the candidate has not completed.

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

Hermes captures `candidate_status` immediately and does not invoke the candidate a second
time. Status 0 or 2 is terminal evidence for review; status 124 is a measured timeout, not
success; status 1 or any other status is a measured failure. No status authorizes migration
or acquisition.

After every status, including 1, 124, or forced termination, Hermes repeats the complete
before snapshot. It records every changed execution-plane identity and proves the lock,
ledger, raw tree, and amendment-ledger state. It must not claim no mutation merely because
the report was not written. If status is 124, it reports checkpoint/cache progress and
stops for review; another resume is not automatically authorized.

For status 0 or 2, record 115 must also contain every candidate-plan, manifest, storage,
membership, Coinalyze, taker-flow, holdout, listing/retry, report, gate, blocker, and sample
field required by review 112, including `migration_authorized=false`,
`download_authorized=false`, and empty `samples`. For a preflight stop, timeout, or failure,
it records all available fields and explicitly identifies those that were not produced.

## Publication

Hermes publishes `research/sprint_004/115_CEX002_PLAN3_CANDIDATE_RESUME.md`, changes both
control files to `Lead Quantitative Finance Researcher/Engineer - inspect review-115
candidate resume`, and leaves next ticket `NONE`. It stages and commits exactly:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/115_CEX002_PLAN3_CANDIDATE_RESUME.md`;
- `tickets/CEX-002.md`; and
- `research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json` only if its bytes changed
  through the candidate process.

Hermes pushes, proves `HEAD == origin/main`, and stops. Data/checkpoint/cache/progress files
remain uncommitted execution state. No unrelated dirty path belongs to the commit.

## Disposition

CEX-002 remains `IN_PROGRESS`. Gate 1 has not passed. Plan migration, sample acquisition,
Gate 2, normalization, catalog publication, Nautilus work, Harmonic Trader work, payoff
analysis, PAPER, LIVE, and every other ticket remain unauthorized. Next ticket remains
`NONE`.
