# CEX-002 Device Preproof False-Negative Correction

- **Date:** 2026-08-27
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** review-322 device preproof false negative corrected; acquisition remains authorized
- **Authorized actor:** Jr Dev - Hermes
- **Gate 2:** in progress; raw acquisition has not started
- **Next ticket:** `NONE`

## Stopped execution

Hermes's first preproof wrapper had a shell-quoting defect before `.env` or the mandated diff
check. Hermes corrected only that wrapper and restarted preproof. The corrected wrapper then
reported `PREPROOF_FAIL: Gate-2 file device` and stopped before acquisition. Hermes performed
no acquisition, verification, repair, edit, commit, push, or accepted-data mutation. The exact
review-322 `git diff --check` has not run.

The reviewer independently opened the SQLite state read-only after the stop. It remained the
accepted plan-only state: zero attempts, sidecars, completions, charges, transitions, runs,
publications, and seals; 202 typed gaps; zero ledger; and the plan receipt as the unchanged
zero-watermark head. No run receipt, content payload, or acquisition process exists.

## Direct device proof

The wrapper result is rejected as a false negative. Direct read-only inspection produced:

```text
gate2_devices
64513
store_devices_and_count
  41809 64513
```

Thus every current entry beneath `data/cex002_qualify/gate2` is on device 64513, and all
41,809 current entries beneath `data/cex002_qualify` are on device 64513. Exact `stat` results
also reported device 64513 for:

- report 62, receipt 258, and attestation 282;
- sample-plan lock, amendment ledger, qualification progress, listing checkpoint, official
  contract metadata, and holdout;
- listing cache, Coinalyze cache, and retained raw content root;
- Gate-2 root, SQLite state, and immutable plan receipt; and
- protected ignored `.env`.

This reviewer proof satisfies review 322's device predicate. The repository, accepted store,
and mounted filesystem all resolve to the same accepted device. No source, authority, state,
or storage correction is required.

## Corrected continuation

Review 322's secure `.env` boundary, full-plan acquisition command, accepted exit 2/3
dispositions, stop conditions, and evidence requirements remain unchanged except that execution
evidence is renamed to record 324 because this correction occupies record 323.

Hermes must not rerun the failed compound wrapper, the device predicate, `plan`, or any
acquisition command already attempted; no acquisition command has yet run. Perform only this
short continuation preproof:

1. confirm synchronized `HEAD == origin/main` at the review-323 publication commit, the review
   exists, all CEX-002 governed repository paths are clean, and no path is staged;
2. prove `.env` remains ignored, regular, owned by `lars`, mode `600`, passes `bash -n`, and
   has a nonempty `COINALYZE_API_KEY`, emitting only boolean results and never the value or its
   length;
3. record current `df -B1 data/cex002_qualify` availability and the ADR-0028 live equation; and
4. run the still-unrun exact `git diff --check` once and retain its exit/output for evidence.

If any continuation predicate fails, stop without acquisition, repair, deletion, edit,
staging, or rerun. If all pass, immediately execute review 322's exact child-subshell
acquisition command once:

```bash
(
  set -a
  . ./.env || exit 5
  set +a
  test -n "${COINALYZE_API_KEY:-}" || exit 5
  export PYTHONDONTWRITEBYTECODE=1
  exec timeout --signal=TERM --kill-after=5m 6h \
    .venv/bin/python scripts/research/acquire_binance_usdm_harmonic_release.py \
    acquire --store-root data/cex002_qualify --max-wall-seconds 21000
)
```

The accepted dispositions remain exit 2 `max_wall_seconds` or exit 3
`complete_with_typed_gaps`, each with a fully published run receipt. Every other disposition
stops exactly as review 322 specifies.

After an accepted exit, follow review 322's read-only reconciliation and publication contract
exactly, but create only:

- `research/sprint_004/324_CEX002_GATE2_FIRST_REAL_ACQUISITION_EXECUTION.md`

Stage only record 324, prove that cached path set, run `git diff --cached --check`, commit with
message `record CEX-002 first real acquisition execution`, push `main`, then run the exact
shared-tree `git diff --check` once and stop for review. No second acquisition/replay, `verify`,
tests, Ruff, control, repair, data deletion, Gate 3, normalization, catalog, NautilusTrader,
Harmonic Trader, experiment, PAPER/LIVE, or next-ticket work is authorized. Gate 2 remains
`IN_PROGRESS`; next ticket remains `NONE`.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly this review,
`docs/handoff/CURRENT_TASK.md`, and `tickets/CEX-002.md`. Developer source/test paths, real
acquisition state/data, execution evidence, `.env`, and unrelated dirty work are excluded.
