# CEX-002 Claude Gate 1 Corrective Source Review

Date: 2026-08-18

Reviewer: Lead Quantitative Finance Researcher/Engineer

Decision: **ACCEPT SOURCE DROP; AUTHORIZE JR INTEGRATION AND REAL GATE 1 EXECUTION**

## Reviewed identities

Committed control-plane base:
`HEAD == origin/main == f1563cb475a7883be9f40ffb7669742f498f1bef`.

| Path | SHA-256 | Bytes |
|---|---|---:|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `4f60ef74478796acb138a34f55ba9f5f9808cbcaff83f0f09310a6cb4a9593a1` | 77,489 |
| `scripts/research/qualify_binance_usdm_harmonic_sources.py` | `af3aca3cf461ce2cfd31dd8db5b4aa53a9c1e5332a7bc8a622f250a3bb2855f6` | 3,127 |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `4ba04c535d81e9a6bac921b9b45844009f72694e48805fafd34a771a75e06abd` | 28,364 |

All fixture hashes remain exactly those recorded in review 63.

## Source acceptance findings

Claude's bounded patch preserves the previously accepted corrections and closes every
review-64 residual:

1. Coverage is evaluated against the full discovered universe by logical product family.
   A symbol with no family prefix is recorded with zero objects, an
   `absent_family_prefix` typed gap, an uncovered-universe identity, and a blocking matrix
   result rather than disappearing.
2. The production Coinalyze transport now retains the atomic download's exact raw bytes,
   SHA-256, byte count, retrieval time, status, and content-addressed path. The client
   rehashes the retained bytes before publishing redacted provenance. The memory transport
   consumes fixture bytes directly under the same contract.
3. The history-symbol mismatch test now expects the implemented history mismatch, and a
   separate test covers a requested market absent from future-markets.

Direct probes reproduced the prior failure cases and now return:

- two-symbol universe with ETH absent from one-minute klines: bar authority
  `sample_only`, `official_complete=False`, `ETHUSDT` in
  `uncovered_universe_symbols`, and an `absent_family_prefix` gap;
- future-markets provenance: reported SHA-256 and byte count exactly equal the retained
  741-byte raw fixture, rather than a canonical JSON reconstruction; and
- the API key is absent from serialized qualification evidence.

No pytest execution by Claude was detected; the target pytest cache predates this patch.

## Reviewer evidence

- In-memory compilation of the three Python paths: PASS.
- Focused Ruff check of the three Python paths: PASS.
- Scoped `git diff --check`: PASS.
- Full-universe absent-prefix direct probe: PASS.
- Raw-response hash/byte identity and secret-absence direct probe: PASS.
- Requested/returned history-symbol direct probe: PASS.
- Pytest and network qualification: not run by the reviewer; these now belong to Hermes.

This is source acceptance only. It is not Gate 1 data acceptance and does not authorize
Gate 2, model work, DEX work, PAPER, or LIVE.

## Jr integration and execution authorization

Jr Dev — Hermes must verify the exact identities above, then integrate only:

- the three reviewed Python paths;
- `tests/acquisition/fixtures/binance_usdm_harmonic_qualification/` at the review-63
  fixture hashes;
- this review, `docs/handoff/CURRENT_TASK.md`, and `tickets/CEX-002.md`; and
- the final real Gate 1 report only after the commands below complete.

Hermes must preserve every unrelated dirty path. It runs, in order:

1. `.venv/bin/python -m pytest tests/acquisition/test_binance_usdm_harmonic_qualification.py -q --tb=short`
2. `.venv/bin/python -m pytest tests/test_download_atomicity.py -q --tb=short`
3. `.venv/bin/python -m ruff check src/cryptofactors/ scripts/`
4. `python3 scripts/check_repo_control.py`
5. `git diff --check`

If either focused suite fails, Hermes records the exact command, exit code, and output and
stops without a network run or source edit.

The ticket's unchanged full-suite command remains mandatory once at final CEX-002 release
acceptance. It is not repeated at every intermediate gate. The already attempted in-place
full suite failed only in preserved, unintegrated DEX/BitMEX paths; record 66 retains the
command, exit code, and failed test identities as nonblocking environmental evidence. No
`-k` substitute and no clean-worktree rerun are required for this Gate 1 integration.

After those commands pass, Hermes runs the real qualifier twice against the same store and
progress file. It loads `.env` without printing it or placing the key in a command argument,
uses `/tmp/cex002_gate1_first.json` for the first report, and uses
`research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json` for the resumed report. An
exit code of 0 means the source matrix qualified; exit code 2 is valid fail-closed
qualification evidence and must not be converted to success. Exit code 1 is an execution
failure and stops publication.

The exact commands are:

1. `/bin/bash -lc 'set -a; . ./.env; set +a; .venv/bin/python scripts/research/qualify_binance_usdm_harmonic_sources.py --store-root data/cex002_qualify --progress-path data/cex002_qualify/cex002_qualification_progress.json --report-path /tmp/cex002_gate1_first.json'`
2. `/bin/bash -lc 'set -a; . ./.env; set +a; .venv/bin/python scripts/research/qualify_binance_usdm_harmonic_sources.py --store-root data/cex002_qualify --progress-path data/cex002_qualify/cex002_qualification_progress.json --report-path research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json'`
3. `.venv/bin/python -c 'import json; from pathlib import Path; from cryptofactors.acquisition.binance_usdm_harmonic_qualification import drop_identity_volatility; a=json.loads(Path("/tmp/cex002_gate1_first.json").read_text()); b=json.loads(Path("research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json").read_text()); assert drop_identity_volatility(a)==drop_identity_volatility(b); print("Gate 1 semantic resume identity: PASS")'`

Hermes compares the two reports after applying the module's identity-volatility projection
and records whether their semantic identities match. It records both command lines, exit
codes, elapsed times, report SHA-256, discovered symbol count, blocked products, sample
count, exact object/byte totals, typed gap counts, Coinalyze raw provenance hashes, and
resume reuse count in
`research/sprint_004/66_CEX002_GATE1_EXECUTION.md`. No secret value may appear.

Hermes commits and pushes only after completing the authorized evidence. The resulting
branch must satisfy `HEAD == origin/main`. If the qualifier is interrupted, Hermes resumes
the same store/progress path until it reaches exit 0, 1, or 2; it must not restart with a
fresh store or silently omit a family. It then stops for reviewer inspection. Gate 2
remains unauthorized.

Before the final evidence commit, Hermes stages only the authorized paths, inspects
`git diff --cached --name-only`, and refuses any unrelated path. It changes the next
required actor in both
`docs/handoff/CURRENT_TASK.md` and `tickets/CEX-002.md` to
`Lead Quantitative Finance Researcher/Engineer — inspect integrated tests and real Gate 1 evidence`.
It does not change ticket state or authorize Gate 2. The integration/evidence commit is
then pushed.
