# CEX-002 Review 491 — Opening price after an empty minute

Reviewer: Lead Quantitative Finance Researcher/Engineer
Senior source actor: Sr Dev — Grok Build (grok-4.7 High)
Ticket: CEX-002, IN_PROGRESS; next ticket NONE

## Evidence and decision

Review 489's source is integrated and pushed at
`e2f2051174ae7f9736b918f54603292d06585177`. Hermes passed 53 tests, scoped Ruff
and repository control. The reviewer matched all five committed blobs to their frozen
hashes. A resumed real comparison exited 1 and retained FAILED report
`809d7d5338985fb0625a823ff8908eeab2c77e9406e5979d2fb8702cd17dfe10`
under `data/.cex002_kline_reconciliation/.reports/`.

All nine days and ten roles have compared hours. There are 167 complete hours,
2,672 compared fields, 2,671 equal fields, no unexplained hourly absence and no coverage
failure. The sole difference is KAIAUSDT, 2025-10-25 10:00 UTC, hourly open:

- Minute 09:59 closes at `0.1075000`.
- Minute 10:00 has open/high/low/close `0.1075000`, zero trades and all four volumes zero.
- Minute 10:01 has two trades and opens at `0.1076000`.
- The accepted hourly open is `0.1076000`; all other compared fields agree.

The reviewer inspected those retained rows directly. Sample manifest is
`f70994ff7d91504570e28c9ac9348f569a5820927a123bac4d6d3bba10f68185`;
the KAIA minute ZIP is
`20c35a9c18294850bbd2dd5e957b3fd9426789d738c425290bb7a4f789f9d606`.
This evidence supports an opening-price rule based on the first minute containing an
executed trade. The current comparator instead selects the empty minute's retained
carry price. Correct the comparator; do not change accepted hourly data or hide the
failure with a price tolerance or exclusion. This refines Review 489's first-open rule
for this observed case, within the existing ticket and architecture.

## Bounded Grok correction

Only these two paths are writable:

- `src/cryptofactors/ingest/binance_usdm_kline_reconciliation.py`
- `tests/ingest/test_binance_usdm_kline_reconciliation.py`

Base source SHA-256: `a175a34e9864d37502641f0dbe652844b464410773a9d0541c22c135a219ed48`.
Base test SHA-256: `a008bb38c0aee5940b92e698885c6a8d64154763c8bf24f020fc94cb8036a64c`.
Acquisition, CLI and acquisition tests remain frozen at Review 489's accepted hashes.

1. For a complete 60-slot hour with trades, independently select the opening price
   from the first minute whose trade count is positive. Empty leading minutes remain
   in the source/accounting and volume/count sums. Preserve the existing high, low,
   close, volume, count and flow calculations, which already match the real evidence.
2. For a complete hour with no trades, preserve the first source opening price as
   an explicitly reported retained-carry case; do not invent a trade or a new price.
   A zero-trade minute with nonzero volume/count-related quantities must fail rather
   than be silently treated as an empty carry minute.
3. Update the declared arithmetic policy and bind the selection in report evidence:
   selected native minute/time/ordinal and source opening token, leading empty-minute
   count, and whether selection used an observed trade or an all-empty retained carry.
   Keep deterministic ordering, existing counts, raw tokens and the 60-slot requirement.
   Other mismatches must still fail. Preserve the original FAILED report unchanged.
4. Add focused fixtures for the observed leading-empty-minute case (explicit expected
   hourly open `0.1076`), multiple leading empty minutes, all-empty carry, invalid
   zero-count/nonzero-volume input, and a deliberately unequal real-trade opening price.
   Keep expected values independent of production aggregation helpers.

No network, real CLI run, data/catalog mutation, Git, records, dependency changes,
unrelated edits, exploratory executable probes or new architecture. Read this bounded
evidence and the two existing paths, then implement directly. After source is ready,
Grok may execute exactly once:

```bash
PYTHONPATH=src .venv/bin/python -m pytest tests/acquisition/test_binance_usdm_kline_comparison_sample.py tests/ingest/test_binance_usdm_kline_reconciliation.py -q --tb=short
```

Stop on its first nonzero result without repair/retry, return exact output and source
hashes/line counts, then stop for reviewer inspection. No Ruff or extra tests assigned.
Later integration and the real offline comparison remain Hermes's work after review.

## Disjoint terminal-record publication

Hermes may concurrently publish the terminal Record 490 for the initial FAILED result,
CURRENT_TASK, tickets/CEX-002.md and this reviewer-authored Review 491: exactly four
paths. It must not stage or edit Grok's two source paths. Record 490 describes source
commit e2f2051 and its captured hashes, not a newly edited worktree. It must disclose the
timeout-validation rejections, unassigned ineffective environment override, reviewer's
interruption (exit 130), explicit resumed run (FAILED, exit 1), and repeated passing
local checks. No offline replay or acceptance claim is assigned after FAILED.

The next actor remains Grok for this correction while Hermes finishes records only.
The reviewer may publish this review and CURRENT_TASK/ticket governance under the
repository exception if needed. One senior source actor, same active ticket, next NONE.

## Source acceptance and local Hermes continuation

The reviewer accepts the two-path correction after static inspection and Grok's one
targeted pytest exited 0 (58 cases). The existing independently authored hourly fixture
keeps its original first-source-open rule; the passing cases explicitly override the
expected traded open, and the mismatch case retains the unequal expectation. High,
low, close and flow arithmetic are unchanged. Report/config policy binds the new rule.

| path | SHA-256 | lines |
| --- | --- | --- |
| src/cryptofactors/ingest/binance_usdm_kline_reconciliation.py | c79de74e3df75a505d2e54c94012fb3a65466736918c6e7ede4d81b8bd3e6741 | 1188 |
| tests/ingest/test_binance_usdm_kline_reconciliation.py | 232d219491ddcc426db31acefdcb61ba7cc7443c690bad2e12ddd0eb9ac12f6c | 1263 |

Automatic approval review rejected the earlier four-path publication prompt because
the new Review 491 Git payload was outside the earlier exact approval. The prompt
requested normal push, not force push. Hermes instead prepared Record 490 locally;
no publication occurred. This local continuation does not bypass that rejection.

Hermes now owns these ordered local steps, stopping at the first nonzero result or
denial without repair/retry. No Git mutation or publication is authorized in this phase.

1. Verify the two accepted hashes and three unchanged Review 489 hashes. Run the same
   targeted pytest once, scoped Ruff on the five source/test/CLI paths once, repository
   control once and whitespace check on the six prospective publication paths.
2. Preserve the existing FAILED report and sample manifest. Capture a small before
   inventory (hash/size/inode/mtime) of the retained sample and existing comparison
   files. Do not inventory or rerun accepted hourly products.
3. Run once, foreground, timeout at most 600 seconds, entirely offline:

   ```bash
   PYTHONPATH=src .venv/bin/python scripts/research/reconcile_binance_usdm_klines.py --repo . --evidence-root data/.cex002_kline_comparison_sample --output-root data/.cex002_kline_reconciliation
   ```

4. If PASS, authenticate the sole completion and its referenced report. Verify 2,672
   matches out of 2,672 fields, 167 complete hours, nine days/ten roles, no discrepancies,
   coverage failures or unexplained absences, and the KAIA 10:01 selected opening token.
   Repeat that exact offline command once; require identical report/completion identities
   and all pre-existing sample/report/completion files unchanged. No network or cleanup.
5. Update Record 490 locally with exact commands, exits, current source identities and
   both real results, explicitly identifying the correction as not yet committed.
   Correct its inaccurate statement that the first two minutes open at 0.1075:
   10:00 opens at 0.1075 with zero trades, and 10:01 opens at 0.1076 with two trades.
   Preserve the original FAILED result and deviations. Then stop for reviewer review.

Prospective publication is exactly the two source/test paths above, Record 490, this
Review 491, CURRENT_TASK and tickets/CEX-002.md (six paths). It remains pending a
concrete review and resolution of the automatic publication block. No bundle work or
next ticket is assigned by this continuation.

## Bounded real-result acceptance and publication package

Hermes's local continuation passed: 58 tests, scoped Ruff, repository control and
six-path whitespace. Both exact offline CLI invocations exited 0, stdout `PASS`.
The reviewer independently authenticated the sole completion and referenced report:

- Completion: `e3c8f9f5ade1b92069b97e6b83931c345886d40901b85b1c4106604edd9b5e5c`.
- Report: `96ae8db169666598643ac4e2f9aa2136b77c0dbeeaa90d2a3e4e4de9e983c89c`.
- All 2,672 fields match across 167 complete hours, nine distinct days and ten roles.
- No discrepancy, coverage failure, unexplained absence or skipped product hour.
- Three partial and 46 absent hours remain explicitly uncomparable; no coverage was fabricated.
- KAIA selects native minute 1, time 1761386460000, ordinal 601, source token
  `0.1076000`, after one empty minute, with selection `observed_trade`.

Hermes's before/after inventory proves all 29 pre-existing files unchanged after the
first run; only the new report and completion were added. Replay preserves all 31
files' SHA-256, size, inode and recorded mtime, with no new, removed or changed file.
The original FAILED report and sample manifest remain unchanged. The inventory records
mtime at integer-second resolution; report/completion content identity is exact.

The reviewer accepts this bounded Gate-4 one-minute/hourly reconciliation against the
frozen correction above. The correction is still uncommitted at this acceptance point;
publication must prove those exact bytes are integrated. This does not accept the full
ticket, bundle, consumer check or unperformed final suite.

The complete publication package is exactly:

1. `src/cryptofactors/ingest/binance_usdm_kline_reconciliation.py`
2. `tests/ingest/test_binance_usdm_kline_reconciliation.py`
3. `research/sprint_004/490_CEX002_KLINE_RECONCILIATION_INTEGRATION_AND_RUN_RECORD.md`
4. `research/sprint_004/491_CEX002_EMPTY_MINUTE_OPEN_CORRECTION_REVIEW.md`
5. `docs/handoff/CURRENT_TASK.md`
6. `tickets/CEX-002.md`

After Record 490 is complete, reviewer inspection and resolution of the automatic
publication block, Hermes may publish only this package: prove HEAD equals origin/main
at e2f2051174ae7f9736b918f54603292d06585177, index empty and accepted source hashes;
run repository control for these final governance bytes; stage precisely the six paths;
prove the staged set and source identities; run staged whitespace; commit with message
`CEX-002: correct empty-minute opening price and record reconciliation`; normal
`git push origin main`; prove HEAD equals origin/main and index empty. Stop on the first
nonzero result or denial. No force push, source/record edits, data command, test rerun,
cleanup, other path or next ticket belongs to this publication phase. Publication stays
pending until the earlier environment approval block is explicitly resolved.

Record 490 is now reviewed and accepted as the execution disclosure, including its
corrected 18-object/29-file count and verbatim local Ruff command. The six-file package
is ready; only resolution of the automatic publication block remains. No further
source, tests, real run or record work is assigned before publication.

The owner subsequently answered yes to committing and pushing this exact six-file
package. That explicit approval resolves the earlier publication block. Hermes may
execute the bounded normal-push workflow above, then return to the reviewer for
committed-byte verification. No additional source, data or next-ticket work is assigned.
