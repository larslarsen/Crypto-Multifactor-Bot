# CEX-002 Review 440 — Review-439 Preflight Acceptance and Existing-Run Monitoring

- **Date:** 2026-09-01
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** accept the Review-439 preflight stop; correct the process-visibility diagnosis; monitor the sole existing conversion to terminal
- **Gate 2:** `ACCEPTED`
- **Gate 3:** `IN_PROGRESS`
- **Next required actor:** Jr Dev — Hermes
- **Next ticket:** `NONE`

## Accepted facts

Hermes correctly stopped Review 439 before creating a directory or launching a process. All commit
and executable hashes passed. Inside the Hermes execution environment, the exact Review-437 shell
PID 1088968 and Python PID 1089049 were still live and the Python child was executing the accepted
production command. The hidden output had advanced far beyond the previously observed 181 pairs.
The Review-439 precondition therefore failed and no Review-439 runner exists.

Immediately after Hermes returned, the reviewer could not resolve those PIDs through the reviewer's
own `/proc` namespace. That absence does not establish process death across execution namespaces.
The shared output provides decisive evidence: after the harness returned, complete Parquet/lineage
pairs increased from 1,973 to 2,017 in 20 seconds, staging was empty at the second observation, and
no completion descriptor yet existed. No second process was launched. The sole previously
authorized Review-437 conversion is alive outside the reviewer's PID namespace and is making
durable forward progress.

Review 439's launch-lifecycle diagnosis is superseded by these observations. The conversion,
accepted input archive, capacity, and source correction are not blocked. The remaining operation is
not acquisition and downloads nothing; it is conversion of the already accepted ZIP contents into
the time-aligned table Harmonic Trader can use.

## Exact continuation

No launch, retry, replacement, signal, cleanup, source/test/CLI edit, test, acquisition, or second
runner is authorized. The reviewer may monitor only read-only shared-output facts while the sole
Review-437 process continues. File-count observations are progress indicators, not acceptance.

At apparent terminal state, one Hermes continuation inspects only the exact Review-437 runner and
its existing hidden output. If the accepted Python identity is live, Hermes returns without
altering it. If it is terminal, Hermes performs the Review-437 success reconciliation when a
completion descriptor exists, or records complete failure evidence when it does not. Hermes then
publishes `research/sprint_004/441_CEX002_OPEN_INTEREST_TERMINAL_RECORD.md`, updates CURRENT_TASK and
this ticket, stages exactly those three record paths, commits, pushes, proves
`HEAD == origin/main`, and stops. There is no reproduction or retry on any terminal result.

On success the reconciliation includes the exact
160,226,578 - 75,255 - 2,818 = 160,148,505 row equation, descriptor-referenced digests and Parquet
metadata rows, lineage outcome counts, preserved prior bytes, the HBAR conflict, typed gaps,
authority counts, and artifact-class byte totals.

No other product, bundle, catalog transaction, NautilusTrader check, experiment, backtest, model,
trading engine, or next ticket is authorized. Gate 2 remains accepted; CEX-002 and Gate 3 remain
`IN_PROGRESS`.

## Reviewer publication scope

Under the AGENTS.md reviewer governance-publication exception this review commits and pushes
exactly:

- `research/sprint_004/440_CEX002_REVIEW439_PREFLIGHT_ACCEPTANCE_AND_EXISTING_RUN_MONITORING.md`;
- `docs/handoff/CURRENT_TASK.md`; and
- `tickets/CEX-002.md`.

The existing process, hidden data, runner evidence, untracked wrapper, and all unrelated dirty
paths remain unstaged and untouched.
