# CEX-002 Clean-Suite Baseline Failure Review

- **Date:** 2026-08-27
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** CEX-002 broad regression evidence accepted with five unrelated baseline
  blockers; remaining clean offline checks authorized
- **Authorized actor:** Jr Dev - Hermes
- **Gate 2:** in progress; no real plan or acquisition authorized
- **Next ticket:** `NONE`

## Accepted same-device run and stop

Hermes completed every review-314 setup proof in detached same-device worktree
`/home/lars/.cache/tmp/cex002-clean-qbGp3y`: repository, receipt, parent, worktree, and copied
receipt were device 64513; clean `PYTHONPATH` and import resolution were proved. The full suite
ran exactly once from `2026-08-27T05:21:53.106341119Z` through
`2026-08-27T06:07:38.778400320Z`, completed in 2,745.672 seconds, and exited 1 with five
failures and no errors. Hermes correctly stopped before Ruff, control, cleanup, evidence,
repair, commit, or push.

The reviewer inspected that new worktree's pytest `lastfailed` cache. It contains exactly:

1. `tests/acquisition/test_uniswap_v2_pair_events.py::TestHeaderBatchEquivalence::test_pilot_style_receipts_without_batch_index_still_replay`
2. `tests/ingest/test_bitmex_funding.py::test_full_backfill_script_dry_run`
3. `tests/universe/test_binding_evidence.py::TestEntrypointCoverage::test_all_eleven_entrypoints_are_discovered`
4. `tests/universe/test_binding_evidence.py::TestEveryBuilderSerializesTheCompleteSeries::test_every_entrypoint_emits_the_complete_series[run_exp009_preregistered_tsmom.py]`
5. `tests/universe/test_binding_evidence.py::TestEveryBuilderSerializesTheCompleteSeries::test_the_series_is_sourced_from_executed_period_logs[run_exp009_preregistered_tsmom.py]`

Pytest completed the full suite, so every other collected test passed or had its declared
non-failure disposition. In particular, no CEX-002 Gate-2 acquisition test failed.

## Attribution

These five failures are independent repository-baseline defects outside CEX-002:

- the committed Uniswap pilot manifest/raw fixture references
  `tests/acquisition/fixtures/uniswap_v2_pair_events_pilot_v1/control.db`, but `.gitignore`
  excludes `*.db`; the 573,440-byte local fixture exists only in the shared worktree and is
  absent from a clean checkout;
- the committed BitMEX dry-run test expects five symbols and 500 rows, while the committed
  script generates six symbols, including `LEGACYUSD`, and 600 rows; and
- the committed tree contains 12 binding entrypoints after restored
  `run_exp009_preregistered_tsmom.py`, while the test expects 11; that restored script also
  lacks the required complete binding-evidence series construction asserted by the other two
  failures.

None of those source, test, or fixture paths was created or changed by the Gate-2 drop. They do
not justify CEX-002 repair under the one-ticket rule. The full ticket acceptance command has
not passed and remains a final repository blocker, but the completed clean run is accepted as
broad CEX-002 regression evidence: the five failures are exactly enumerated and unrelated, and
all Gate-2 tests passed.

## Remaining clean checks

Hermes must remove only failed temporary worktree
`/home/lars/.cache/tmp/cex002-clean-qbGp3y` through forced Git worktree removal. Do not remove
or alter any other worktree. Confirm synchronized shared `HEAD == origin/main` with this review
present, the review-313 Gate-2 hashes and clean status, and no staged path. Create a unique new
detached worktree under `/home/lars/.cache/tmp` at current `HEAD`; repeat the numeric device,
clean `PYTHONPATH`, and import-resolution proofs from review 314. Do not copy, symlink, or
overlay the ignored Uniswap database or any shared dirty source/test path.

From that new clean worktree, run exactly once in order:

```bash
.venv/bin/python -m ruff check src/cryptofactors/ scripts/
python3 scripts/check_repo_control.py
```

If setup or either command fails, stop immediately without repair, rerun, later command,
evidence edit, commit, push, or temporary-worktree removal. Return the exact failure and full
command result.

If and only if both commands pass, remove only that new worktree, return to the shared tree,
and create exactly:

- `research/sprint_004/316_CEX002_GATE2_OFFLINE_VALIDATION_EXECUTION.md`

Record the complete reviews 308-315 validation history, integration commit, all Gate-2 hashes,
the exact five unrelated full-suite blockers, clean-suite totals and timing, both new exact
commands and their timestamps/timing/output, every clean-tree environment proof, and clean
Gate-2 status. State explicitly that final ticket-wide pytest acceptance remains blocked by
the five unrelated baseline defects and was not converted to a pass.

Stage only record 316, prove the cached path and run `git diff --cached --check`, commit with
message `record CEX-002 Gate-2 offline validation`, and push `main`. Then run the ticket's exact
`git diff --check` once in the shared worktree and report its exit code. Do not amend or rerun
if it fails.

Stop with the evidence commit, pushed remote, every command result, final hashes, exact clean
Gate-2 status, and remaining unrelated shared status. No baseline-defect repair, source/test
change, real `plan`, `acquire`, or `verify` operation, network access, accepted-data/state
mutation, Gate 3, normalization, catalog, NautilusTrader, Harmonic Trader, PAPER/LIVE, or
next-ticket work is authorized.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly this review,
`docs/handoff/CURRENT_TASK.md`, and `tickets/CEX-002.md`. Developer source/test paths,
state/data/evidence, and unrelated dirty work are excluded.
