# CEX-002 Environment Secret Boundary and Full Acquisition Correction

- **Date:** 2026-08-27
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** review-321 command superseded; one bounded full-plan acquisition run authorized
- **Authorized actor:** Jr Dev - Hermes
- **Gate 2:** in progress; raw acquisition has not started
- **Next ticket:** `NONE`

## New operator fact

After review 321 was published, the owner reported that the Coinalyze API key is stored in the
repository-root `.env`. The reviewer checked only safe predicates and did not read or print the
value:

- `.env` is a regular file, mode `600`, owned by user and group `lars`;
- Git ignores it under `.gitignore:40`;
- it contains a nonempty `COINALYZE_API_KEY` entry; and
- `bash -n .env` exits 0 without output; and
- the accepted CLI does not load `.env`; it reads only
  `os.environ.get("COINALYZE_API_KEY")`.

Review 321's observation that the key was unset in the reviewer process was correct but
incomplete: the secret existed on disk without being exported. No source change or provider
investigation is needed.

## Superseded boundary

This review supersedes only review 321's acquisition command, Binance-only object ceiling,
expected disposition, and evidence record number. Review 321's plan acceptance, independent
receipt/state reconciliation, capacity facts, governed hashes, and all prohibitions remain
accepted.

Do not execute review 321's `--max-objects 736274` command. Because the free-source secret is
available through the protected local environment file, the authorized run should remain
bounded by time while being allowed to traverse the complete immutable plan. Removing the
operational object ceiling does not expand or alter economic scope; it avoids an unnecessary
stop before the 570 accepted Coinalyze logical receipts.

The secret is loaded only inside a child subshell. It is not placed in a prompt, command-line
argument, repository record, URL, query identity, log, receipt, exception, or parent-shell
environment. Sourcing the owner-controlled file is accepted here because its ownership, mode,
ignore rule, and required nonempty entry were proved immediately before authorization.

## Corrected Hermes execution

Hermes owns one real full-plan acquisition invocation and one evidence publication. Preserve
every unrelated modified or untracked path. Do not rerun `plan`.

Preproof must establish without accepted-data mutation:

- synchronized `HEAD == origin/main`, with review 322, review-321 commit `a4fbbed`,
  record-320 commit `05003b2`, and review-319 commit `0e3cea2` in ancestry;
- unchanged accepted acquisition source, CLI, test, record 318, plan receipt, and plan
  identities/hashes;
- clean status for all CEX-002 governed repository paths and no staged path;
- the exact accepted read-only plan-state counts and zero-watermark head in review 321;
- all Gate-2 files and authorities on device 64513;
- current capacity sufficient under the live ADR-0028 equation; and
- `.env` remains an ignored regular file, mode `600`, owned by `lars`, with a nonempty
  `COINALYZE_API_KEY` entry and passing `bash -n`, proving only boolean predicates and never
  the value or its length.

Record 320 did not establish the required post-publication diff result. Run one fresh exact
`git diff --check` during this preproof and retain its complete result for record 323. If it
exits nonzero, stop without acquisition or edit. Do not search an agent transcript and do not
run it more than once in this round.

If any other preproof fails, stop without acquisition, repair, deletion, edit, staging, or
rerun and return the exact failed predicate. If it passes, record pre-run `df -B1` capacity and
run exactly once from the repository root:

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

The accepted dispositions are:

- exit 2 with stop reason `max_wall_seconds`: normal resumable full-plan progress; or
- exit 3 with stop reason `complete_with_typed_gaps`: every required downloadable object and
  all accepted typed gaps completed inside the bound.

Exit 0 is inconsistent with the 202 accepted typed gaps. Exit 4, 5, 6, outer-timeout status,
signal termination without a closed run receipt, secret exposure, state/authentication
failure, or any other result stops without repair, deletion, rerun, later command, evidence
edit, commit, or push and returns the exact result for review.

## Exit-2/3 evidence

Only after an accepted exit with a fully published run receipt, create exactly:

- `research/sprint_004/323_CEX002_GATE2_FIRST_REAL_ACQUISITION_EXECUTION.md`

Use filesystem/JSON/hash inspection and SQLite `mode=ro` with `PRAGMA query_only=ON`; do not
invoke the acquisition module or CLI for inspection. Record:

- exact command, UTC start/end, elapsed time, exit, stdout/stderr, and stop reason;
- pre/post live capacity equations and available-byte observations;
- run receipt and locator paths, identities, byte lengths, canonical body, predecessor equal
  to the prior head, seal/head linkage, and exact high-watermarks;
- exact pre/post/delta plan, attempt, sidecar, completion, gap, charge, transition, run,
  publication, seal, listed-byte, and content-file facts;
- retained adoption count/bytes and exact remaining Binance/Coinalyze counts;
- durable attempt count equal to network-call count, bounded redacted network/error samples,
  retry/outcome counts, and provider/family completion totals;
- Coinalyze request count, one-symbol request shape, 40-per-minute limiter, ledger charge versus
  the 30,580,702-byte ceiling, charge-transition settlement, and typed response outcomes;
- boolean secret-absence scans over database bytes, receipts, captured output, exceptions,
  evidence, and any persisted URL/query fields, using the sourced value internally but never
  printing it or its length;
- content/sidecar physical bytes, deduplicated identities, partial-file absence, and terminal
  artifact absence;
- observed completion, network-call, and byte throughput plus, for exit 2, a clearly labeled
  remaining-duration estimate derived only from this real run; and
- the review-322 pre-acquisition `git diff --check` command and exact result.

For exit 3, reconcile exactly 736,347 Binance completions, all 570 Coinalyze logical receipts,
202 typed gaps, zero pending plan entries, zero open charges, and the full retained/new byte
equations. Do not run the replay or terminal verifier in this round; those remain separate
acceptance boundaries.

Do not run `acquire` again, `verify`, tests, Ruff, control, qualification, sizing, capacity
attestation, normalization, or any later-gate command. Stage only record 323, prove that exact
cached path set, run `git diff --cached --check`, commit with message
`record CEX-002 first real acquisition execution`, and push `main`. Run the ticket's exact
shared-tree `git diff --check` once after push and report it. Stop for reviewer acceptance with
the pushed commit, record hash/length, receipt identities, reconciliation, throughput/estimate,
clean governed status, and preserved unrelated status.

No second acquisition session, replay, terminal verification, source/test repair, authority
refresh, data deletion, Gate 3, normalization, catalog, NautilusTrader, Harmonic Trader,
experiment, PAPER/LIVE, or next-ticket work is authorized. Gate 2 remains `IN_PROGRESS`; next
ticket remains `NONE`.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly this review,
`docs/handoff/CURRENT_TASK.md`, and `tickets/CEX-002.md`. Developer source/test paths, real
acquisition state/data, execution evidence, `.env`, and unrelated dirty work are excluded.
