# CEX-002 Review 449 — Record 448 Acceptance and Hourly Kline Resume

- **Date:** 2026-09-02
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** accept integration and timeout evidence; authorize one identical resume with a 3,600-second execution allowance
- **Gate 2:** `ACCEPTED`
- **Gate 3:** `IN_PROGRESS`
- **Next required actor:** Jr Dev — Hermes
- **Next ticket:** `NONE`

## Decision

Record 448 is accepted. Hermes integrated exactly the three Review-447 paths at commit
`f9613e2b74a7eb9933271073f3bf8a4c99a676fe`, passed all 43 focused tests, lint, and repository
control, and pushed the source unchanged. The real command then exited 124 exactly at the harness's
600-second execution limit. No normalizer exception, authority failure, economic failure, unsafe
state, or content collision was observed.

The timeout left matching clean progress in both hidden roots: 6,787 Parquet partitions and 6,787
lineages per product, empty staging directories, no gap artifact, and no completion descriptor.
The process is absent and the counts remained stable after Hermes returned. Generation 0 is
unchanged and nothing was downloaded. This is a harness-duration failure, not a data or source
defect.

At the observed rate, a fresh full pass projects to about 2,001 seconds. Resume must parse and
reprove the already published prefix before advancing, so this review uses a 3,600-second execution
allowance rather than another 600-second limit. No source, test, CLI, output, or authority change is
needed.

## Fixed resume pre-state

- `HEAD == origin/main == d82aa3f114519b2926c2e3905767543bac2fadeb` before this review publication;
- integrated source SHA-256 `d553e5aea9d58f0bd80ef39e5ab9d1bc6a7e566e2ac8aacaf66b81f36eb8ddd4`;
- integrated CLI SHA-256 `f1a4df5065de841f15d1bbbb1692b98bf97a010c37f7294f9230d0c02d240542`;
- `data/.cex002_bar_1h`: 6,787 Parquets, 6,787 lineages, empty `.staging`, no completion or gap artifact;
- `data/.cex002_trade_flow_1h`: 6,787 Parquets, 6,787 lineages, empty `.staging`, no completion or gap artifact;
- observed available bytes after interruption: 43,601,747,968; and
- protected capacity floor: 33,566,545,257 bytes.

## Hermes authorization

Hermes performs only this ordered workflow:

1. Reprove `HEAD == origin/main`, the two integrated hashes, both exact partial inventories, empty
   staging, absent completion/gap artifacts, no running kline normalizer, and available bytes at or
   above 33,566,545,257. Any mismatch stops without launch.
2. Confirm before launch that its command-execution mechanism can keep one unified foreground
   session alive and observable for at least 3,600 seconds. A mechanism capped at 600 seconds is not
   usable and must stop without launch.
3. Run exactly one identical command from the repository root:

```text
PYTHONPATH=src .venv/bin/python scripts/research/normalize_binance_usdm_klines.py \
  --generation0-state data/cex002_qualify/gate2/state.sqlite \
  --generation0-content-root data/cex002_qualify/gate2/content \
  --bar-output-root data/.cex002_bar_1h \
  --trade-flow-output-root data/.cex002_trade_flow_1h
```

Hermes remains attached to that one unified execution session until terminal. A yielded command
session may be waited on without relaunch; this is not a PID polling loop. The execution allowance
is 3,600 seconds. There is no wrapper, detach, second process, second invocation, retry, signal,
cleanup, output deletion, or source change.

On every terminal outcome Hermes publishes
`research/sprint_004/450_CEX002_HOURLY_KLINE_RESUME_RECORD.md` with matching CURRENT_TASK and ticket
changes, commits/pushes only those three paths, and returns both actor fields to the reviewer.

For status zero, Record 450 includes exact start/end/runtime/stdout, source commit, completion
paths/hashes, source/byte/partition/row/gap totals, output bytes, staging contents, and full
descriptor-referenced Parquet/lineage/schema/digest reconciliation. For any nonzero status or lost
terminal evidence, it records exact facts and stops without diagnosis-by-guess, retry, or cleanup.

## Prohibitions

No test, lint, integration, source/test/CLI edit, acquisition, network data call, V3 input, cleanup,
catalog transaction, NautilusTrader work, experiment, backtest, model, Harmonic Trader repository
work, PAPER, LIVE, other product, or next ticket is authorized. The untracked repository runner
must not be read, edited, staged, or invoked.

## Reviewer publication scope

The reviewer publishes exactly this review, CURRENT_TASK, and CEX-002. All source, data, runner, and
unrelated dirty paths remain unstaged and untouched.
