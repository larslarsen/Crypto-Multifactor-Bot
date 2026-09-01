# CEX-002 Review 434 — Record 433 Acceptance and Path-Identity Resume

- **Date:** 2026-09-01
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** accept the terminal facts; reject the blocker diagnosis; restore the accepted relative authority identities for one resume
- **Gate 2:** `ACCEPTED`
- **Gate 3:** `IN_PROGRESS`
- **Next required actor:** Jr Dev — Hermes
- **Next ticket:** `NONE`

## Record 433 acceptance

`HEAD == origin/main == f9aa7717a1c8757ae9a147a08d44fe5a82d18519`. Record 433 accurately
states the sole Review-432 runner identity, nonempty process start ticks, 42-second duration,
terminal exit 1, exact traceback, unchanged hidden output, and absence of retry or data mutation.
The normalizer correction remains accepted and integrated at commit `a243932…`.

The record's terminal facts are accepted. Its suggestion that the embedded receipt intent itself
is inconsistent is rejected by the exact path comparison below.

## Exact read-only path diagnosis

The generation-0 `run_publication` table contains one distinct accepted `receipt_directory`
string:

```text
data/cex002_qualify/gate2/run_receipts
```

`AcquisitionState.__init__` deterministically derives `run_receipt_dir` as
`Path(state_path).parent / "run_receipts"`. `_authenticate_run_publication` requires the stored
`Path(receipt_directory)` to equal that derived path without silently resolving or rewriting
either identity.

Review 432 passed the state path as
`/home/lars/Crypto_Multifactor_Bot/data/cex002_qualify/gate2/state.sqlite`, so the derived directory
was `/home/lars/Crypto_Multifactor_Bot/data/cex002_qualify/gate2/run_receipts`. It correctly did not
equal the accepted repository-relative identity. The earlier production commands used
`data/cex002_qualify/gate2/state.sqlite`; that derived the exact stored identity and authenticated
successfully through the point where eight months were published.

Therefore the Review-432 failure was caused solely by changing authority arguments from their
accepted relative identities to absolute strings. No receipt, database, raw object, acquisition,
normalizer, or source code is defective or authorized for repair.

## One corrected supervisor

Hermes performs read-only prechecks equivalent to Review 432, additionally proving the
`run_publication` value above and the Review-432 runner's terminal identity. It does not rerun
pytest or ruff and does not edit any repository file.

After every precheck passes, Hermes creates exactly one mode-0700 supervisor beneath one literal
`/tmp/cex002_oi_434_XXXXXX` directory. The supervisor must:

1. set `REPO_ROOT=/home/lars/Crypto_Multifactor_Bot` and successfully `cd "$REPO_ROOT"` before
   recording or launching anything;
2. use the absolute interpreter and CLI paths below, while preserving every accepted authority
   and output argument exactly as a repository-relative string:

```text
PYTHONPATH=/home/lars/Crypto_Multifactor_Bot/src
/home/lars/Crypto_Multifactor_Bot/.venv/bin/python
/home/lars/Crypto_Multifactor_Bot/scripts/research/normalize_binance_usdm_open_interest.py
--generation0-state data/cex002_qualify/gate2/state.sqlite
--generation0-content-root data/cex002_qualify/gate2/content
--v3-manifest data/cex002_qualify/gate2_revision_candidate_v3/manifest/4dacaba97c17ad9c4a9724f5db74dfab7ee98760cdb3df6dea46ab37c0684c2d.json.gz
--recovery-root data/cex002_recovery
--output-root data/.cex002_open_interest_5m
```

3. durably record the literal working directory, exact command, source commit, start/end UTC,
   shell and Python PID/start-tick pairs, persistent stdout/stderr, and exit code using Review
   432's supervisor contract; and
4. perform no other operation.

Hermes launches that one supervisor with `nohup setsid`, closed stdin, and all supervisor output
redirected inside the runner directory. It confirms one nonempty shell/Python identity pair and
returns immediately without waiting for completion. It must not use, edit, stage, or replace the
untracked repository wrapper.

There is no second launch for any reason. Missing metadata, wrong command text, wrong working
directory, an empty start tick, immediate failure, or uncertainty is terminal and cannot be
corrected or retried under this review. A live process is never signaled.

## Continuation and terminal evidence

Later Hermes continuations inspect only the exact reported runner. At terminal they publish
`research/sprint_004/435_CEX002_OPEN_INTEREST_RESUME_RECORD.md`, update CURRENT_TASK and the ticket
with both actor fields returned to the reviewer, stage exactly those three record paths, commit,
push, prove `HEAD == origin/main`, and stop. On success they perform all Review-430 reconciliation,
including prior artifact-byte reuse and the May-03 exclusion, typed gap, and May-04-owned value.

No source/test/CLI patch, repeated test, database or receipt mutation, acquisition, network
request, redownload, cleanup, deletion, duplicate or replacement runner, other product, final
bundle, catalog transaction, NautilusTrader check, experiment, backtest, model, trading engine, or
next ticket is authorized.

Under the AGENTS.md reviewer governance-publication exception this review commits and pushes
exactly:

- `research/sprint_004/434_CEX002_RECORD433_ACCEPTANCE_AND_PATH_IDENTITY_RESUME.md`;
- `docs/handoff/CURRENT_TASK.md`; and
- `tickets/CEX-002.md`.

All integrated source, hidden data, terminal evidence, the untracked wrapper, and every unrelated
dirty path remain untouched.
