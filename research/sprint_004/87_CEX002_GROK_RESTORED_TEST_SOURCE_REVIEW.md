# CEX-002 Grok Restored Test Source Review

Date: 2026-08-20

Reviewer: Lead Quantitative Finance Researcher/Engineer

Decision: **ACCEPT AND INTEGRATE RESTORED TEST SOURCE; AUTHORIZE HERMES COMMANDS AND
BOUNDED REAL GATE 1 QUALIFICATION/RESUME**

## Reviewed state

Committed control-plane base:
`HEAD == origin/main == 434784c4c4187884a42efe3848723b56cb7c2cf9`.

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `7e60ed28d56a32b1722d9c6016ff059c188dfed71481aa5865ca367767d14150` |
| `scripts/research/qualify_binance_usdm_harmonic_sources.py` | `578f45e2be6f4428cc73560daacb31a305f72501f26f4ea2cd2c718a444fc64b` |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `8076ea28b2f4c69e434afe60e7132f922eb2d322649365782117709b2260131f` |
| `tests/acquisition/fixtures/binance_usdm_harmonic_qualification/exchange_info.json` | `9388b67710c51ce0a4219c2e23d57c804d01f4a54b08b340dff1e9bdbb414ed0` |
| `tests/acquisition/fixtures/binance_usdm_harmonic_qualification/coinalyze_future_markets.json` | `47416908780ef674efdf1cb3a62cb215c4f48834ad932f9c20e080eb6649b83f` |
| `tests/acquisition/fixtures/binance_usdm_harmonic_qualification/coinalyze_liquidation_history_anchors.json` | `d4e7834b6705e8c21329c04fa9738c29030e1da9c674b7d57e9ba4f3977e9ad0` |
| `tests/acquisition/fixtures/binance_usdm_harmonic_qualification/coinalyze_open_interest_history_anchors.json` | `30be3ac8ba27213a381675f24a6f83b6de85d139032662101d14e9f8d626f9df` |
| `tests/acquisition/fixtures/binance_usdm_harmonic_qualification/coinalyze_funding_rate_history_anchors.json` | `2537212f7b423a991a4ed9aa2413df72843dc059768e53f23260eddfe5de1f3f` |
| `tests/acquisition/fixtures/binance_usdm_harmonic_qualification/coinalyze_ohlcv_history_anchors.json` | `8fd1ddd5eb4b498badc4b203831872b3c1b006fb892f196f6d5273932d0de6d5` |

Only the test path changed under review 86. Production, CLI, and fixtures remain at their
accepted hashes. Every unrelated dirty path remains excluded.

## Acceptance findings

The session-history restoration returns the focused source to 3,669 lines and 135 unique
test functions. The review-75 membership, immutable-plan, cumulative-budget, physical
storage, coverage-state, and stable-anchor sections are present. Review-76 crash-safe
ledger, retained metadata, verified storage, temporal-window, and complete-gap coverage is
present. Review-77 raw authority, plan-input, ledger-validation, and full Coinalyze
identity coverage is present. Review-78/79 volatile-response, rejected-authority
nonmutation, reduced-ledger, rehash, and transferred/no-transfer coverage is present.

Spark's five corrected test contracts remain incorporated, including affirmative current
membership for the oversized fixture and immutable first-plan facts separated from
execution reuse. No duplicate test function names were found. The 51 production symbols
reported unused in record 85 again support substantive restored assertions.

The reviewer ran no pytest, Ruff, acceptance command, network command, or data mutation.
This is source acceptance only, not Gate 1 data acceptance.

## Reviewer integration

At the owner's explicit direction, the reviewer preserves the accepted drop in Git
immediately rather than adding a separate Hermes handoff for a brief staging operation.
The reviewer stages and commits exactly the nine reviewed source/test/fixture paths plus
the three review/control paths enumerated below, pushes, and establishes
`HEAD == origin/main` before Hermes executes commands.

The reviewer runs no test, lint, acceptance, network, or data command. No `git restore`,
`git checkout`, `git reset`, stash, clean, or destructive equivalent is authorized. A
later failure is corrected forward from this preserved commit.

## Hermes command authorization

Hermes then runs in order:

1. `.venv/bin/python -m pytest tests/acquisition/test_binance_usdm_harmonic_qualification.py -q --tb=short`
2. `.venv/bin/python -m pytest tests/test_download_atomicity.py -q --tb=short`
3. `.venv/bin/python -m ruff check src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py scripts/research/qualify_binance_usdm_harmonic_sources.py tests/acquisition/test_binance_usdm_harmonic_qualification.py`
4. `python3 scripts/check_repo_control.py`
5. `git show --check --oneline --no-renames HEAD`

The full suite remains deferred to final CEX-002 release acceptance. No `-k`, source or
fixture edit, clean-worktree reconstruction, DEX/BitMEX command, or data deletion is
authorized. A failure is recorded exactly in
`research/sprint_004/88_CEX002_GATE1_STABLE_AUTHORITY_EXECUTION.md`; Hermes changes both
control files to the reviewer, publishes only those three paths, and stops before network.
The candidate source commit remains preserved.

## Bounded real execution

After all five commands pass, Hermes performs the two preserved-store real runs and
semantic identity assertion specified in review 80, using:

- first report: `/tmp/cex002_gate1_stable_first.json`;
- second report: `research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json`.

It must not delete, rename, replace, reconstruct, or relock `data/cex002_qualify`. The API
key is loaded only from `.env` into the environment and never printed or placed in a
command argument. Exit 0 is qualified, exit 2 is honest blocked evidence, and exit 1 stops
the second run. Record 88 contains every command, exit, elapsed time, hash, and exact
membership/plan/ledger/storage/coverage/sample/listing/retry/Coinalyze/metadata/progress
metric required by review 80, with no secret value.

Before final evidence publication, Hermes changes both control files to
`Lead Quantitative Finance Researcher/Engineer - inspect Gate 1 stable-authority
execution`. It stages only those two files, record 88, and report 62 when a new second-run
report exists; verifies the staged list; commits; pushes; establishes
`HEAD == origin/main`; and stops.

## Reviewer publication and integration set

At the owner's explicit direction, this acceptance and integration commit is confined to:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/87_CEX002_GROK_RESTORED_TEST_SOURCE_REVIEW.md`; and
- `tickets/CEX-002.md`;
- `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py`;
- `scripts/research/qualify_binance_usdm_harmonic_sources.py`;
- `tests/acquisition/test_binance_usdm_harmonic_qualification.py`;
- `tests/acquisition/fixtures/binance_usdm_harmonic_qualification/exchange_info.json`;
- `tests/acquisition/fixtures/binance_usdm_harmonic_qualification/coinalyze_future_markets.json`;
- `tests/acquisition/fixtures/binance_usdm_harmonic_qualification/coinalyze_liquidation_history_anchors.json`;
- `tests/acquisition/fixtures/binance_usdm_harmonic_qualification/coinalyze_open_interest_history_anchors.json`;
- `tests/acquisition/fixtures/binance_usdm_harmonic_qualification/coinalyze_funding_rate_history_anchors.json`; and
- `tests/acquisition/fixtures/binance_usdm_harmonic_qualification/coinalyze_ohlcv_history_anchors.json`.

No other source, test, fixture, data, prior record, or unrelated dirty path belongs to this
commit.

## Disposition

CEX-002 and Gate 1 remain `IN_PROGRESS` pending Hermes evidence. Gate 2, Nautilus
integration, every other ticket, and Harmonic Trader work remain unauthorized. Next
ticket remains `NONE`.
