# CEX-002 Storage-Sizing Test Source Acceptance

**Date:** 2026-08-22  
**Reviewer:** Lead Quantitative Finance Researcher/Engineer  
**Decision:** `ACCEPTED_FOR_HERMES_RESTART`  
**Gate 1:** Accepted  
**Gate 2:** Not accepted; real sizing has not run

## Accepted correction

Spark changed only `tests/acquisition/test_binance_usdm_harmonic_sizing.py`. The accepted
SHA-256 is
`e7b7103cb36f83642762a91101be98ae368ba41b425f8a3e00711632895da6de`, with exactly 44
`def test_` functions.

The diff is exactly review 186's two mechanical corrections:

- deterministic fixture gzip creation now uses `gzip.GzipFile(..., mtime=0)`; and
- the literal-pin test reads the existing `sizing` module without reloading it or replacing
  the imported `SizingError` class identity.

No test was added, removed, weakened, or otherwise changed. Production and CLI remain
frozen at:

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py` | `795eab0312064e3d7be7dd8f826b5dc5754a8e6b5e702872ac3699dad1532390` |
| `scripts/research/size_binance_usdm_harmonic_release.py` | `78ee687c734fc94070952d290752acdbd007970fb26c616e5e6845f1de3702ad` |

## Hermes restart

Jr Dev - Hermes must start from the committed review-187 control plane, prove
`HEAD == origin/main`, verify the three hashes and 44-test count above, integrate only the
accepted sizing-test diff, and preserve every unrelated dirty path unstaged and
byte-identical.

Hermes restarts the review-184 sequence from its first command:

```bash
.venv/bin/python -m pytest \
  tests/acquisition/test_binance_usdm_harmonic_sizing.py -q --tb=short

.venv/bin/python -m ruff check \
  src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py \
  scripts/research/size_binance_usdm_harmonic_release.py \
  tests/acquisition/test_binance_usdm_harmonic_sizing.py

python3 scripts/check_repo_control.py
```

The first nonzero result stops all later commands and is recorded without source repair,
retry, or substitution. Only after all three commands exit zero, Hermes runs review 184's
exact local sizing command once, proves the fixed receipt and content-addressed envelopes,
then runs that exact command once more to prove byte-identical fixed-target reproof. A
`blocked` storage measurement is honest evidence, not a command failure and not Gate-2
acceptance.

Hermes publishes the restart in
`research/sprint_004/188_CEX002_STORAGE_SIZING_RESTART_AND_EXECUTION.md`, including every
command, exit code, transcript, elapsed time, artifact identity, capacity field, envelope
count/bytes, absence of partial files, and exact Git scope. Hermes updates
`docs/handoff/CURRENT_TASK.md` and `tickets/CEX-002.md` for reviewer inspection, runs
path-restricted `git diff --check`, stages only the corrected test, receipt 180 if created,
record 188, and those two control files, commits, pushes, proves `HEAD == origin/main`, and
stops.

The local content-addressed sizing envelopes are recorded but not committed. Hermes runs
no network call, credential load, qualification, bulk acquisition, normalization, catalog
publication, Gate-2 acceptance, NautilusTrader, Harmonic Trader, payoff, PAPER, LIVE,
paid-source, reduced-scope, or next-ticket work. Next ticket remains `NONE`.
