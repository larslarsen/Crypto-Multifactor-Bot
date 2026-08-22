# CEX-002 Storage-Sizing Ruff Source Acceptance

**Date:** 2026-08-22
**Reviewer:** Lead Quantitative Finance Researcher/Engineer
**Decision:** `ACCEPTED_FOR_HERMES_RESTART`
**Gate 1:** Accepted
**Gate 2:** Not accepted; real sizing has not run

## Accepted correction

Claude deleted exactly the three unused imports authorized by review 193 and changed no
other byte. The accepted test SHA-256 is
`fda45c767e8cf271136f2a25769e37f64c57428fde15e508d0045b975679b2c7`, with 44
`def test_` functions. Production and CLI remain frozen at:

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py` | `795eab0312064e3d7be7dd8f826b5dc5754a8e6b5e702872ac3699dad1532390` |
| `scripts/research/size_binance_usdm_harmonic_release.py` | `78ee687c734fc94070952d290752acdbd007970fb26c616e5e6845f1de3702ad` |

## Hermes restart

Jr Dev - Hermes must start from the committed review-194 control plane, prove
`HEAD == origin/main`, verify all three hashes and the 44-test count, integrate only the
accepted test diff, and preserve every unrelated dirty path unstaged and byte-identical.

Run the focused test, exact-path Ruff, and repository-control commands from review 191 in
order. Stop at the first nonzero result. Only after all three pass, run review 184's exact
local sizing command once, prove receipt 180 and all content-addressed sizing envelopes,
then run the identical command once more. The second invocation must say `re-proved`,
publish zero envelopes, and return the exact first receipt hash and size.

Publish all results in
`research/sprint_004/195_CEX002_STORAGE_SIZING_VERIFICATION_AND_EXECUTION.md`. Record every
command, exit code, transcript, elapsed time, receipt field/hash/size, envelope
count/bytes/hashes, partial-file absence, capacity fields, and exact Git scope. Update the
two control records for reviewer inspection, run path-restricted `git diff --check`, stage
only the accepted test, receipt 180 if created, record 195, and the two control records,
commit, push, prove `HEAD == origin/main`, and stop.

Local sizing envelopes remain uncommitted evidence. Hermes runs no network call,
credential load, qualification, bulk acquisition, normalization, catalog publication,
Gate-2 acceptance, NautilusTrader, Harmonic Trader, payoff, PAPER, LIVE, paid-source,
reduced-scope, or next-ticket work. Next ticket remains `NONE`.
