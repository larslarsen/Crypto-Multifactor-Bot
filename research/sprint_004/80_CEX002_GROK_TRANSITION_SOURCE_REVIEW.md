# CEX-002 Grok Transition Source Review

Date: 2026-08-20

Reviewer: Lead Quantitative Finance Researcher/Engineer

Decision: **ACCEPT SOURCE DROP; AUTHORIZE HERMES INTEGRATION AND BOUNDED REAL GATE 1
QUALIFICATION/RESUME**

## Reviewed state

Committed control-plane base:
`HEAD == origin/main == fe3e25da93c61b95dadc721d278584507dd1b129`.

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `7e60ed28d56a32b1722d9c6016ff059c188dfed71481aa5865ca367767d14150` |
| `scripts/research/qualify_binance_usdm_harmonic_sources.py` | `578f45e2be6f4428cc73560daacb31a305f72501f26f4ea2cd2c718a444fc64b` |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `f30c341234286975434fa481c665a1cbb60438ea9a891889bef0ebbab7e0f7e6` |
| `tests/acquisition/fixtures/binance_usdm_harmonic_qualification/exchange_info.json` | `9388b67710c51ce0a4219c2e23d57c804d01f4a54b08b340dff1e9bdbb414ed0` |
| `tests/acquisition/fixtures/binance_usdm_harmonic_qualification/coinalyze_future_markets.json` | `47416908780ef674efdf1cb3a62cb215c4f48834ad932f9c20e080eb6649b83f` |
| `tests/acquisition/fixtures/binance_usdm_harmonic_qualification/coinalyze_liquidation_history_anchors.json` | `d4e7834b6705e8c21329c04fa9738c29030e1da9c674b7d57e9ba4f3977e9ad0` |
| `tests/acquisition/fixtures/binance_usdm_harmonic_qualification/coinalyze_open_interest_history_anchors.json` | `30be3ac8ba27213a381675f24a6f83b6de85d139032662101d14e9f8d626f9df` |
| `tests/acquisition/fixtures/binance_usdm_harmonic_qualification/coinalyze_funding_rate_history_anchors.json` | `2537212f7b423a991a4ed9aa2413df72843dc059768e53f23260eddfe5de1f3f` |
| `tests/acquisition/fixtures/binance_usdm_harmonic_qualification/coinalyze_ohlcv_history_anchors.json` | `8fd1ddd5eb4b498badc4b203831872b3c1b006fb892f196f6d5273932d0de6d5` |

Grok changed only the production and test paths authorized in review 79. The other seven
paths are the unchanged accumulated CEX-002 CLI/fixture drop accepted through reviews 76
to 78. Every DEX/BitMEX path and transient database sidecar remains unrelated and
excluded.

## Acceptance findings

Review 79's two defects are closed:

1. The live exchangeInfo response and candidate first-closed observation are staged in
   memory. Classification and immutable plan comparison use the staged semantic view;
   the content-addressed response and metadata checkpoint are committed only after an
   existing plan accepts its inputs or the first plan is established.
2. A focused three-response test establishes `TRADING`, rejects `SETTLING`, proves both
   durable metadata artifacts stayed byte-identical, and then resumes the original plan
   and semantic identity with fresh volatile response provenance.
3. The no-transport acquisition path now uses the retained checksum sidecar's proved
   digest to locate and rehash an existing content address before any raw fetch.
4. A proved existing object skips the raw fetch and settles with explicit no-transfer;
   an absent destination fetches the raw object and records its full transferred size,
   even if content identity could otherwise be shared.
5. Focused fetch-log and ledger assertions cover both transitions.

The stable provenance/semantic split, fail-closed contract semantics, structured ledger,
and every earlier accepted source-authority, retry, checkpoint, storage, coverage, and
Coinalyze closure remain represented. Static inspection found no remaining source-level
blocker.

The reviewer ran no pytest, Ruff, acceptance command, network command, or data mutation.
This is source acceptance only, not Gate 1 data acceptance.

## Hermes integration authorization

Jr Dev - Hermes verifies all nine hashes above, preserves every unrelated dirty path, and
runs in order:

1. `.venv/bin/python -m pytest tests/acquisition/test_binance_usdm_harmonic_qualification.py -q --tb=short`
2. `.venv/bin/python -m pytest tests/test_download_atomicity.py -q --tb=short`
3. `.venv/bin/python -m ruff check src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py scripts/research/qualify_binance_usdm_harmonic_sources.py tests/acquisition/test_binance_usdm_harmonic_qualification.py`
4. `python3 scripts/check_repo_control.py`
5. `git diff --check`

The monorepo full suite remains deferred to final CEX-002 release acceptance. No `-k`,
clean-worktree reconstruction, DEX/BitMEX command, source edit, fixture edit, or data
deletion is authorized.

If any command fails, Hermes writes the exact failure to
`research/sprint_004/81_CEX002_GATE1_STABLE_AUTHORITY_EXECUTION.md`, changes the next
required actor in `docs/handoff/CURRENT_TASK.md` and `tickets/CEX-002.md` to
`Lead Quantitative Finance Researcher/Engineer - inspect Gate 1 stable-authority
execution`, publishes only those three records, establishes `HEAD == origin/main`, and
stops without a network run.

After all five commands pass, Hermes stages exactly the nine reviewed source/test/fixture
paths, verifies `git diff --cached --name-only` and every staged SHA-256, commits with
message `CEX-002: integrate stable authority qualifier`, pushes, and establishes
`HEAD == origin/main` before network execution.

## Bounded real execution authorization

Hermes then runs the qualifier against the existing `data/cex002_qualify` store. It must
not delete, rename, replace, reconstruct, or relock that store. Existing raw objects,
listings, checkpoints, reports, and over-budget legacy evidence are preserved. The API key
is loaded only from `.env` into the environment and is never printed or placed in a
command argument.

First run:

`/bin/bash -lc 'set -a; . ./.env; set +a; .venv/bin/python scripts/research/qualify_binance_usdm_harmonic_sources.py --store-root data/cex002_qualify --progress-path data/cex002_qualify/cex002_qualification_progress.json --report-path /tmp/cex002_gate1_stable_first.json'`

Exit 0 is qualified, exit 2 is an honest blocked matrix, and exit 1 is execution failure.
For exit 1, Hermes stops network work but still records and publishes durable
checkpoint/retry/store evidence. It does not claim success.

If the first run exits 0 or 2, Hermes runs the same qualifier a second time with report:

`research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json`

It then runs:

`.venv/bin/python -c 'import json; from pathlib import Path; from cryptofactors.acquisition.binance_usdm_harmonic_qualification import drop_identity_volatility; a=json.loads(Path("/tmp/cex002_gate1_stable_first.json").read_text()); b=json.loads(Path("research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json").read_text()); assert drop_identity_volatility(a)==drop_identity_volatility(b); print("Gate 1 semantic resume identity: PASS")'`

Hermes records commands, exit codes, elapsed time, report hashes, exact membership class
counts, blocking candidates, plan version/digest/input identities, ledger reservations,
transferred/no-transfer charges, legacy range, physical storage requirement/credit/
capacity/shortfall, per-product source and coverage states, complete typed gaps, sample and
listing reuse/fetch counts, retry incidents, Coinalyze anchor/support/provenance evidence,
metadata row/snapshot identities, progress/checkpoint identities, and retained-store size
in record 81. No secret value may appear.

Before every final evidence publication, including a focused-command or real-run failure,
Hermes changes the next required actor in both control files to
`Lead Quantitative Finance Researcher/Engineer - inspect Gate 1 stable-authority
execution`. It stages only those two control files, record 81, and report 62 when a new
second-run report exists; verifies the staged path list; commits; pushes; establishes
`HEAD == origin/main`; and stops.

## Reviewer publication

Under the narrow reviewer-publication exception, this acceptance publication is confined
to:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/80_CEX002_GROK_TRANSITION_SOURCE_REVIEW.md`; and
- `tickets/CEX-002.md`.

No source, test, fixture, data, prior report, or unrelated dirty path is part of this
publication. The reviewer executes no tests or acceptance commands.

## Disposition

CEX-002 and Gate 1 remain `IN_PROGRESS` pending Hermes evidence. Gate 2, Nautilus
integration, every other ticket, and Harmonic Trader work remain unauthorized. Next
ticket remains `NONE`.
