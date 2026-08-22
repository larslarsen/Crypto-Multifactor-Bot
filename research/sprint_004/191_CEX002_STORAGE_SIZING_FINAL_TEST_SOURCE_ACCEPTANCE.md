# CEX-002 Storage-Sizing Final Test Source Acceptance

**Date:** 2026-08-22  
**Reviewer:** Lead Quantitative Finance Researcher/Engineer  
**Decision:** `ACCEPTED_FOR_HERMES_RESTART`  
**Gate 1:** Accepted  
**Gate 2:** Not accepted; real sizing has not run

## Accepted correction

Spark changed only `tests/acquisition/test_binance_usdm_harmonic_sizing.py`. The accepted
SHA-256 is
`585f20db0461ad92af7cf6b1d4143aa52c4dfdff5f2bbfa44e76d4f6334e9f96`, with exactly 44
`def test_` functions.

The accepted diff now:

- selects exactly one non-consumable row from each of the 12 physical families;
- retains exact beyond-`2**53` rational comparisons and inspects only the arithmetic
  helpers for forbidden float conversion;
- uses the real `projected_coinalyze_receipts` receipt field;
- accepts both fail-closed outcomes only for the content-addressed envelope symlink; and
- restores the independent receipt-publication and prior-receipt symlink expectations.

The omitted textual `/` scan is nonblocking: it confused Python path joining with numeric
division, while the production helpers have been statically inspected and the dynamic
cross-multiplication assertions remain. The long generator expression does not violate
the configured Ruff rule set. No further Spark work is authorized.

Production and CLI remain frozen at:

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py` | `795eab0312064e3d7be7dd8f826b5dc5754a8e6b5e702872ac3699dad1532390` |
| `scripts/research/size_binance_usdm_harmonic_release.py` | `78ee687c734fc94070952d290752acdbd007970fb26c616e5e6845f1de3702ad` |

## Hermes restart

Jr Dev - Hermes must start from the committed review-191 control plane, prove
`HEAD == origin/main`, verify the three hashes and 44-test count above, integrate only the
accepted test diff, and preserve every unrelated dirty path unstaged and byte-identical.

Run in order, stopping at the first nonzero result:

```bash
.venv/bin/python -m pytest \
  tests/acquisition/test_binance_usdm_harmonic_sizing.py -q --tb=short

.venv/bin/python -m ruff check \
  src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py \
  scripts/research/size_binance_usdm_harmonic_release.py \
  tests/acquisition/test_binance_usdm_harmonic_sizing.py

python3 scripts/check_repo_control.py
```

Only after all three exit zero, run review 184's exact local sizing command once. Prove
the fixed receipt and every content-addressed sizing envelope, then run the identical
command exactly once more. The second invocation must say `re-proved`, publish zero
envelopes, and return the exact first receipt hash and size. A `blocked` storage state is
honest measurement evidence, not command failure and not Gate-2 acceptance.

Publish all results in
`research/sprint_004/192_CEX002_STORAGE_SIZING_FINAL_RESTART_AND_EXECUTION.md`. Record every
command, exit code, transcript, elapsed time, receipt field summary/hash/size, envelope
count/bytes/hashes, absence of partials, capacity fields, and exact Git scope. Update
`docs/handoff/CURRENT_TASK.md` and `tickets/CEX-002.md` for reviewer inspection, run
path-restricted `git diff --check`, stage only the accepted test, receipt 180 if created,
record 192, and those two control files, commit, push, prove `HEAD == origin/main`, and
stop.

Local content-addressed sizing envelopes are evidence but are not committed. Hermes runs
no network call, credential load, qualification, bulk acquisition, normalization, catalog
publication, Gate-2 acceptance, NautilusTrader, Harmonic Trader, payoff, PAPER, LIVE,
paid-source, reduced-scope, or next-ticket work. Next ticket remains `NONE`.
