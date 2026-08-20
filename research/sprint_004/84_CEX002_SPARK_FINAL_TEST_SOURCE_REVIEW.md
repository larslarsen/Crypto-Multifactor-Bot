# CEX-002 Spark Final Test Source Review

Date: 2026-08-20

Reviewer: Lead Quantitative Finance Researcher/Engineer

Decision: **ACCEPT TEST SOURCE; AUTHORIZE HERMES INTEGRATION AND BOUNDED REAL GATE 1
QUALIFICATION/RESUME**

## Reviewed state

Committed control-plane base:
`HEAD == origin/main == 1c90415d829822edfdbad78baee243faf6d24f9e`.

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `7e60ed28d56a32b1722d9c6016ff059c188dfed71481aa5865ca367767d14150` |
| `scripts/research/qualify_binance_usdm_harmonic_sources.py` | `578f45e2be6f4428cc73560daacb31a305f72501f26f4ea2cd2c718a444fc64b` |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `d2e172e90cdda8f2740b4b53fe213a019e374750aeb2db3db49e4b508e4a4ae5` |

The seven review-80 fixture hashes remain unchanged. Spark changed only the authorized
test path. The accepted production module and CLI remain byte-identical. Every unrelated
dirty path remains excluded.

## Acceptance findings

All five review-82 test-contract defects are now closed:

1. Current authenticated contracts with no archive prefix expect `current_unarchived`.
2. Nonblocking family-launch temporal gaps retain official authority through the typed
   source and coverage states.
3. The oversized-object fixture supplies both declared trade groups, contiguous periods,
   and affirmative current-perpetual membership, while asserting no raw oversized fetch.
4. The resume test preserves the original locked plan's one new object, zero retained
   objects, zero retained bytes, and positive planned download bytes; checkpoint reuse and
   an unchanged single transferred ledger charge are asserted separately.
5. The missing-row-fields test supplies an authenticated response envelope.

The unused local assignment left during the intermediate correction is removed. Grok's
review-79 durability and transfer tests and every previously accepted integrity test
remain present.

The reviewer ran no pytest, Ruff, acceptance command, network command, or data mutation.
This is test-source acceptance only, not Gate 1 data acceptance.

## Hermes authorization

Hermes verifies all nine hashes from review 80, substituting the accepted test hash above,
and preserves every unrelated dirty path. It runs in order:

1. `.venv/bin/python -m pytest tests/acquisition/test_binance_usdm_harmonic_qualification.py -q --tb=short`
2. `.venv/bin/python -m pytest tests/test_download_atomicity.py -q --tb=short`
3. `.venv/bin/python -m ruff check src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py scripts/research/qualify_binance_usdm_harmonic_sources.py tests/acquisition/test_binance_usdm_harmonic_qualification.py`
4. `python3 scripts/check_repo_control.py`
5. `git diff --check`

The full suite remains deferred to final CEX-002 release acceptance. No `-k`, source or
fixture edit, clean-worktree reconstruction, DEX/BitMEX command, or data deletion is
authorized. A failure is recorded exactly in
`research/sprint_004/85_CEX002_GATE1_STABLE_AUTHORITY_EXECUTION.md`; Hermes changes both
control files to the reviewer, publishes only those three paths, and stops before network.

After all commands pass, Hermes stages exactly the nine reviewed paths, verifies the
staged path list and hashes, commits with message
`CEX-002: integrate stable authority qualifier`, pushes, and establishes
`HEAD == origin/main`.

Hermes then performs the two preserved-store real runs and semantic identity assertion
specified in review 80, with these report paths:

- first run: `/tmp/cex002_gate1_stable_first.json`;
- second run: `research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json`.

It must not delete, rename, replace, reconstruct, or relock `data/cex002_qualify`. The API
key is loaded only from `.env` into the environment and is never printed or placed in a
command argument. Exit 0 is qualified, exit 2 is honest blocked evidence, and exit 1 stops
the second run. Record 85 must contain every command and exit, elapsed time, hashes, exact
membership/plan/ledger/storage/coverage/sample/listing/retry/Coinalyze/metadata/progress
metric required by review 80, with no secret value.

Before final evidence publication, Hermes changes both control files to
`Lead Quantitative Finance Researcher/Engineer - inspect Gate 1 stable-authority
execution`. It stages only those two files, record 85, and report 62 when a new second-run
report exists; verifies the staged list; commits; pushes; establishes
`HEAD == origin/main`; and stops.

## Reviewer publication

Under the narrow reviewer governance exception, this acceptance publication is confined
to:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/84_CEX002_SPARK_FINAL_TEST_SOURCE_REVIEW.md`; and
- `tickets/CEX-002.md`.

No source, test, fixture, data, prior record, or unrelated dirty path belongs to this
publication. The reviewer executes no tests or acceptance commands.

## Disposition

CEX-002 and Gate 1 remain `IN_PROGRESS` pending Hermes evidence. Gate 2, Nautilus
integration, every other ticket, and Harmonic Trader work remain unauthorized. Next
ticket remains `NONE`.
