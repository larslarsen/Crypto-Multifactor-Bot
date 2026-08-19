# CEX-002 Claude Test Source Review

Date: 2026-08-18

Reviewer: Lead Quantitative Finance Researcher/Engineer

Decision: **ACCEPT TEST SOURCE; AUTHORIZE HERMES INTEGRATION AND BOUNDED REAL GATE 1 RESUME**

## Reviewed state

Committed control-plane base:
`HEAD == origin/main == cd3afd2ae812a2b7998d811bc7b2821e86634b5f`.

| Path | SHA-256 | Decision |
|---|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `3e8d14887f0f9e273a3fc00c3fd1b5d640cf01ad4214049a050df8425a5480d0` | review-70 acceptance unchanged |
| `scripts/research/qualify_binance_usdm_harmonic_sources.py` | `40d944a8149e22cd917fa3097009c53307bc5c9614ef35139f4317b1843e6f8a` | review-70 acceptance unchanged |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `c32b74f543c9254c81579a0275364b943a262c35f3b72050fa9560dbc7abdb90` | accepted in this review |

Claude changed only the test path authorized by review 72. The production module and CLI
still match review 70 exactly. Every unrelated dirty path remains outside CEX-002 scope.

## Acceptance findings

The corrected test source closes review 72:

1. A fixed ZIP member timestamp makes separately constructed clean and resumed indexes
   byte-stable.
2. The target abort/resume test derives valid headerless-trade archive bytes from each
   remote key, giving the six test objects distinct content addresses.
3. After the injected abort, the test proves the sample store contains exactly the two
   completed raw digests before resume.
4. The resumed run must not fetch either completed raw key, must fetch every genuinely
   absent raw key, and must have the same semantic identity as the uninterrupted run.
5. Separate same-digest tests prove cross-key adoption avoids redundant raw retrieval when
   the exact sidecar filename, sidecar content address, provider checksum, and rehashed raw
   bytes agree.
6. Parameterized broken-leg cases and a tampered-raw case prove inconsistent evidence is
   not silently recovered.

The correction preserves the production content-addressed recovery contract instead of
requiring redundant network work. No duplicate test function names are introduced.

No pytest, Ruff, acceptance command, network command, or data-mutating probe was run by the
reviewer. This is source acceptance only, not Gate 1 data acceptance.

## Hermes integration authorization

Hermes verifies the three hashes above, preserves every unrelated dirty path, and runs in
order:

1. `.venv/bin/python -m pytest tests/acquisition/test_binance_usdm_harmonic_qualification.py -q --tb=short`
2. `.venv/bin/python -m pytest tests/test_download_atomicity.py -q --tb=short`
3. `.venv/bin/python -m ruff check src/cryptofactors/ scripts/`
4. `python3 scripts/check_repo_control.py`
5. `git diff --check`

The monorepo full suite remains deferred to final CEX-002 release acceptance. No `-k`,
clean-worktree reconstruction, DEX/BitMEX command, source edit, or data deletion is
authorized. If a command fails, Hermes writes the exact failure to
`research/sprint_004/74_CEX002_GATE1_RESUMABLE_EXECUTION.md`, changes the next required
actor in `docs/handoff/CURRENT_TASK.md` and `tickets/CEX-002.md` to
`Lead Quantitative Finance Researcher/Engineer — inspect Gate 1 resumable execution`,
publishes only those three records, establishes `HEAD == origin/main`, and stops without a
network run.

After all five commands pass, Hermes stages only the three reviewed source/test paths,
verifies `git diff --cached --name-only`, commits with message
`CEX-002: integrate resumable bounded Gate 1 qualifier`, pushes, and establishes
`HEAD == origin/main` before network execution.

## Bounded real execution authorization

Hermes then runs the real qualifier against the existing `data/cex002_qualify` store. It
must not delete, rename, replace, or reconstruct that store. It loads `.env` without
printing it or placing the key in a command argument.

First run:

`/bin/bash -lc 'set -a; . ./.env; set +a; .venv/bin/python scripts/research/qualify_binance_usdm_harmonic_sources.py --store-root data/cex002_qualify --progress-path data/cex002_qualify/cex002_qualification_progress.json --report-path /tmp/cex002_gate1_resumable_first.json'`

Exit 0 is qualified, exit 2 is an honest blocked matrix, and exit 1 is execution failure.
For exit 1, Hermes stops network work but still records and publishes durable
checkpoint/retry/store evidence. It does not claim success.

If the first run exits 0 or 2, Hermes runs the same qualifier a second time with report:

`research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json`

It then runs:

`.venv/bin/python -c 'import json; from pathlib import Path; from cryptofactors.acquisition.binance_usdm_harmonic_qualification import drop_identity_volatility; a=json.loads(Path("/tmp/cex002_gate1_resumable_first.json").read_text()); b=json.loads(Path("research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json").read_text()); assert drop_identity_volatility(a)==drop_identity_volatility(b); print("Gate 1 semantic resume identity: PASS")'`

Hermes records commands, exits, elapsed time, report hashes, exact object/byte totals,
symbol and blocked-product counts, sample plan and new-download bytes, recovered/reused
samples, listing checkpoint claimed/reused/fetched/unclaimed counts, retry incidents,
Coinalyze provenance, progress/checkpoint identities, and retained-store size in record 74.
No secret value may appear.

Before every final evidence publication, including a focused-command or real-run failure,
Hermes changes the next required actor in `docs/handoff/CURRENT_TASK.md` and
`tickets/CEX-002.md` to
`Lead Quantitative Finance Researcher/Engineer — inspect Gate 1 resumable execution`. It
stages only those two records, record 74, and the real report when one exists; verifies the
staged path list; commits; pushes; establishes `HEAD == origin/main`; and stops.

## Reviewer publication

Under the narrow reviewer-publication exception, this acceptance publication is confined
to:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/73_CEX002_CLAUDE_TEST_SOURCE_REVIEW.md`; and
- `tickets/CEX-002.md`.

No test or acceptance command is part of this publication. The reviewer stages, commits,
and pushes only those paths while preserving every source/test drop and unrelated dirty
path.

## Gate decision

CEX-002 and Gate 1 remain `IN_PROGRESS`. Gate 2, every other ticket, and model work remain
unauthorized. Next ticket remains `NONE`.
