# CEX-002 Corrected Plan Acceptance and First Acquisition

- **Date:** 2026-08-27
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** corrected plan accepted; one bounded full-plan acquisition session authorized
- **Authorized actor:** Jr Dev - Hermes
- **Gate 2:** in progress; first corrected raw acquisition authorized
- **Next ticket:** `NONE`

## Record disposition

Hermes amended only record 339 in pushed commit
`3cdc268d963b6fe3bfacc5e28e6f15ccd1ece7f8`. Its final SHA-256 is
`fc794479cb52376d4139fdec047e89bf858393c92216006c10ea1ad4e913fac1`, 296 lines.

The record now contains the complete 5,007-byte two-space-indented canonical receipt and its
exact SHA-256
`c0b973b2c794804b543225c119eeb8a9fb17798473774859fa92abacca7b9167`, plus the shell
and standard-library SQLite scripts used for read-only reconciliation.

Review 342 makes one explicit presentation correction instead of routing another record-only
round. The inventory and SQLite blocks are normalized summaries of the script-derived facts,
not byte-for-byte raw stdout. In particular, GNU `find` `%d` is traversal depth rather than
device, and Python `print("name=", value)` emits a separating space. The independently bound
device fact remains `dev:64513` in the exact receipt and accepted store binding; the normalized
inventory values are consistent with that binding. This correction supersedes only the
record's use of "exact captured output" for those rendered blocks. It does not alter any plan
fact.

The reviewer accepts record 339 when read with this correction. No plan rerun or further
evidence presentation work is authorized.

## Accepted corrected plan

The accepted plan command ran once, network-free, in 171.325 seconds with exit 0. The plan is:

- receipt schema `cex002_gate2_plan_receipt_v2` under policy
  `adr0029_content_addressed_gate2_acquisition_and_resume_adr0030_exact_retained_credit_v2`;
- semantic identity
  `8d96db46d5b6df45e4b9c0ba0e45ae9f3688dd88503195fb426e12de827bde22`, distinct from
  rejected identity
  `911ed811ba5a04008fa787ee88eb4b38a4df3718b169b5c5d914e9ac2f30f578`;
- exactly 737,119 rows: 736,347 Binance, 1 Coinalyze inventory, 569 Coinalyze liquidation,
  and 202 typed unsupported gaps;
- exactly 73 retained Binance objects, 5,225,416 bytes, 68 selected keys, 5 cost keys, and
  0 unverified objects under key-set digest
  `5e13a9fbb57acff21d0c290d3f0da7c27d549031fdee1fca8a1ab0744cc0b982`;
- 736,274 other Binance rows explicitly unretained and 772 Coinalyze rows not applicable to
  retained credit;
- 20,351,715,427 projected new Binance raw bytes plus 30,580,702 projected new Coinalyze raw
  bytes, totaling 20,382,296,129 bytes; and
- integrity-clean, foreign-key-clean, zero-fact state with an uncharged ledger and
  zero-watermark head bound to the new receipt.

Post-plan availability was 248,392,949,760 bytes. Under ADR-0028, the contemporaneous
49,678,589,952-byte renewable reserve plus 139,577,980,018-byte stable requirement totals
189,256,569,970 bytes, leaving 59,136,379,790 bytes of headroom. The acquisition must
recompute the live equation before scheduling.

This is the complete harmonic-ready raw plan. It is not price-only, does not include trades or
`aggTrades`, and does not include full historical books. It does include the accepted bars,
metrics/open-interest, funding, mark/index/basis, liquidation, and bounded real book cost
calibration inputs.

## First corrected acquisition boundary

The protected repository-root `.env` contains the free-source `COINALYZE_API_KEY`. The value
must remain absent from prompts, command arguments, parent environment, URLs, persisted query
identities, database bytes, receipts, logs, exceptions, and evidence. The accepted CLI reads
only the child process environment.

The engine wall bound is 21,000 seconds (5 hours 50 minutes), leaving ten minutes for durable
settlement before the six-hour outer process bound. There is no object ceiling: the session may
traverse the entire immutable Binance and Coinalyze plan. This does not broaden economic scope.

Accepted dispositions are:

- exit 2 with `max_wall_seconds`: normal resumable full-plan progress; or
- exit 3 with `complete_with_typed_gaps`: every downloadable object completed with the 202
  accepted typed gaps.

Exit 0 is inconsistent with the accepted typed gaps. Any other exit, timeout/signal without a
closed run receipt, secret exposure, or state/authentication error is rejected without repair
or rerun.

## Hermes execution authorization

Hermes owns one acquisition invocation and execution record 343. Preserve every unrelated
modified and untracked path. Do not rerun `plan`.

Repository-only preproof must establish:

- `HEAD == origin/main`, Review 342 is present, and record-339 correction commit
  `3cdc268d963b6fe3bfacc5e28e6f15ccd1ece7f8` is an ancestor of `HEAD`;
- record-339 SHA-256
  `fc794479cb52376d4139fdec047e89bf858393c92216006c10ea1ad4e913fac1`;
- acquisition source SHA-256
  `af6ef568b9f0f30827b393efc013b13560d4fd5761ec86417c0d2cf461e1248d`, acquisition test
  SHA-256 `40a75c4e8516f94e9d7528ec036bd7fef964219ac2203768f510364ff30d2624`,
  and acquisition CLI SHA-256
  `6f4b56ecb43dcc448eb6c8cf765e38d9fa3923432459574d913582e3d9c84043`;
- no staged path and no `.git/index.lock`;
- `docs/handoff/CURRENT_TASK.md`, `tickets/CEX-002.md`, ADR-0030, Review 342, and record 339
  are clean; and
- `.env` remains Git-ignored, regular, owned by `lars`, mode `600`, passes `bash -n`, and has a
  nonempty `COINALYZE_API_KEY`, emitting only boolean predicates and never the value or length.

Do not repeat the prior full device/tree preproof. The accepted plan and acquisition engine own
path/device/authority authentication. Record pre-run `df -B1 data/cex002_qualify` availability
and require the live ADR-0028 equation to pass. Any failed preproof stops without acquisition,
repair, reset, restore, checkout, stash, data mutation, or rerun.

On preproof success, record exact UTC start time and invoke exactly once from repository root:

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

Capture complete bounded stdout/stderr, exact UTC end time, elapsed time, and exit status. Do
not retry or run a second acquisition for any disposition.

After any actual invocation returns, create exactly:

- `research/sprint_004/343_CEX002_FIRST_CORRECTED_REAL_ACQUISITION_EXECUTION.md`.

For every exit, record the repository commit, exact source/CLI/plan identities, exact command,
pre-run capacity equation, UTC timing, elapsed time, exit status, and complete bounded
stdout/stderr. For any unaccepted exit, publish only those captured facts, state that no later
data command followed, and stop for review.

Only for accepted exit 2 or 3 with a fully published run receipt, use accurately labeled
read-only filesystem/JSON/hash summaries and standard-library SQLite `mode=ro` plus immediate
`PRAGMA query_only=ON` to record:

- run receipt and locator paths, SHA-256/bytes/canonical body, predecessor/head/seal linkage,
  exact watermarks, stop reason, and start/end snapshots;
- exact pre/post/delta attempt, sidecar, completion, gap, charge, transition, run, publication,
  seal, listed-byte, physical-content, and pending-plan facts;
- retained adoption count/bytes and remaining Binance/Coinalyze counts;
- durable attempt count versus network calls, bounded redacted error/outcome/retry samples,
  provider/family completion totals, and partial/terminal artifact absence;
- Coinalyze request shape/rate, ledger ceiling/settlement, typed outcomes, and boolean proof
  that the secret value occurs nowhere in captured output or persisted URL/query/database/
  receipt/evidence fields, without printing the secret or its length;
- pre/post capacity, observed throughput, and for exit 2 a clearly labeled remaining-duration
  estimate derived only from this real session; and
- for exit 3, exact reconciliation of 736,347 Binance completions, all 570 Coinalyze logical
  receipts, 202 typed gaps, zero pending entries, zero open charges, and full byte equations.

Normalized summaries are permitted when labeled as such; do not call transformed output
verbatim or raw. Do not run replay or `verify` even on exit 3.

Use explicit Git-write escalation. Stage only record 343, prove that exact cached one-path set,
run `git diff --cached --check`, commit with message
`record CEX-002 first corrected acquisition`, push `main`, and stop for reviewer acceptance.
If record or Git publication fails, do not rerun acquisition or inspect/mutate state beyond the
already-authorized accepted-exit reconciliation; return the captured result and failure.

No second acquisition, replay, terminal verification, source/test repair, authority refresh,
data deletion, Gate 3, normalization, catalog, NautilusTrader, Harmonic Trader, experiment,
PAPER/LIVE, or next-ticket work is authorized. Gate 2 remains `IN_PROGRESS`; next ticket
remains `NONE`.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly this review,
`docs/handoff/CURRENT_TASK.md`, and `tickets/CEX-002.md`. Developer evidence, state/data,
`.env`, and unrelated dirty work are excluded.
