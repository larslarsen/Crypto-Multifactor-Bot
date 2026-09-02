# CEX-002 Review 447 — Hourly Kline Source Acceptance and Real Run

- **Date:** 2026-09-02
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** accept the Review-446 source/test drop and authorize Hermes integration plus one local conversion
- **Gate 2:** `ACCEPTED`
- **Gate 3:** `IN_PROGRESS`
- **Next required actor:** Jr Dev — Hermes
- **Next ticket:** `NONE`

## Source acceptance

The reviewer inspected the complete Review-446 production, CLI, and test source. Sol changed only
the three new authorized paths. Their exact identities are:

| path | SHA-256 | lines |
|---|---|---:|
| `src/cryptofactors/ingest/binance_usdm_klines.py` | `d553e5aea9d58f0bd80ef39e5ab9d1bc6a7e566e2ac8aacaf66b81f36eb8ddd4` | 1,042 |
| `scripts/research/normalize_binance_usdm_klines.py` | `f1a4df5065de841f15d1bbbb1692b98bf97a010c37f7294f9230d0c02d240542` | 49 |
| `tests/ingest/test_binance_usdm_klines.py` | `b95d16614063043fe9a0d3eeb0e0cf63e9196b05c7e26f18cbd94162cb510a2a` | 482 |

Sol used the one targeted senior exception exactly once:

```text
PYTHONPATH=src .venv/bin/python -m pytest tests/ingest/test_binance_usdm_klines.py -q --tb=short
...........................................                              [100%]
```

The command exited zero with 25 test functions and 43 collected/passing cases. Sol ran no other
test, lint, compile, format, Git, network, real-data, SQLite, acquisition, integration, record,
cleanup, or unrelated-path command.

Static review confirms that the drop:

- authenticates the fixed generation-0 SQLite schema, domains, singleton/prefix receipts, seal
  head, total Binance completion count, exact daily/monthly counts and bytes, accepted validation
  states, plan identities, sidecar checksums, content paths, content hashes, and raw bytes;
- accepts only canonical one-hour daily/monthly USD-M kline identities and rejects mixed-family
  symbol/month authority before publication;
- reads each authenticated ZIP once, handles only the exact headed or headerless 12-field shape,
  retains exact integer/decimal source values, and enforces timestamp, filename-period, OHLC,
  nonnegative volume/count, and taker-buy-within-total rules;
- produces the accepted bar and trade-flow schemas separately, with exact context-independent
  taker-sell and buy-minus-sell imbalance arithmetic and the accepted native/reference identity;
- rejects every duplicate, preserves the original per-object row ordinal, and maps every
  partition-local raw reference to exact source lineage;
- detects within-object and between-object missing-hour runs, splits only at UTC month boundaries,
  publishes no invented market row, and writes a typed gap artifact for each product;
- publishes bounded product/symbol/month Parquet and lineage artifacts using the accepted writer,
  content addressing, atomic no-clobber, collision verification, two distinct hidden roots, and
  completion-last semantics; and
- enforces the full-corpus source, byte, partition, row, and gap totals before either product can
  receive its completion descriptor.

The complete Review-446 test contract is represented, including header form, exact values, all four
flow derivations, daily/monthly authority, overlap, duplicate/conflict, within/cross-object gaps,
cross-month gap splitting, schemas, native identity, lineage, separate roots, completion equations,
interruption, replay, differing content-address collision, unsafe ZIP members, symlinked raw input,
finite row bounds, validation states, plan binding, substitute database rejection, and hidden/distinct
output roots.

This accepts source for Jr integration. It does not accept either real product and does not accept
Gate 3.

## Fixed pre-state

At review time:

- `HEAD == origin/main == 4214104c8a5e5a87a708da20009b8a649eca7274`;
- `data/.cex002_bar_1h` is absent;
- `data/.cex002_trade_flow_1h` is absent;
- filesystem available bytes are 45,717,274,624; and
- the protected Review-446 real-run floor is 33,566,545,257 bytes.

Every unrelated modified/untracked path remains outside this review, including the untracked
repository runner. Hermes must not read, edit, stage, invoke, clean, restore, or otherwise use
`run_continuation_runner.sh`.

## Hermes integration and command authorization

Jr Dev — Hermes is authorized for this exact ordered workflow only.

### 1. Reprove the drop and pre-state

Hermes verifies `HEAD == origin/main`, the three exact hashes and line counts above, the absence of
both output roots, and that no additional Review-446 path exists. A mismatch stops without editing,
testing, staging, or running data.

### 2. Run the focused checks in order

Stop on the first nonzero status:

```text
PYTHONPATH=src .venv/bin/python -m pytest tests/ingest/test_binance_usdm_klines.py -q --tb=short
PYTHONPATH=src .venv/bin/python -m ruff check --no-cache src/cryptofactors/ingest/binance_usdm_klines.py scripts/research/normalize_binance_usdm_klines.py tests/ingest/test_binance_usdm_klines.py
python3 scripts/check_repo_control.py
```

No full suite is authorized at this intermediate product boundary.

### 3. Integrate exactly three paths

Hermes stages only the three accepted paths, verifies that the cached path set is exact, runs
`git diff --cached --check`, commits them with a CEX-002 hourly-kline integration message, pushes,
and proves `HEAD == origin/main`. No unrelated path may be staged or included. The three hashes must
remain exact after the commit.

### 4. Reprove capacity and destinations

Hermes obtains the destination filesystem's integer available-byte count immediately before the
real command. It must be at least 33,566,545,257. Both exact output roots must still be absent and
must not be symlinks. A failed capacity or destination precondition stops without creating either
root.

### 5. Execute one foreground local conversion

Hermes runs exactly one invocation from the repository root and remains attached until it is
terminal:

```text
PYTHONPATH=src .venv/bin/python scripts/research/normalize_binance_usdm_klines.py \
  --generation0-state data/cex002_qualify/gate2/state.sqlite \
  --generation0-content-root data/cex002_qualify/gate2/content \
  --bar-output-root data/.cex002_bar_1h \
  --trade-flow-output-root data/.cex002_trade_flow_1h
```

This command downloads nothing and does not change the accepted generation-0 authority. There is no
second invocation or retry for any reason. No wrapper, detached supervisor, duplicate process, PID
polling loop, signal, cleanup, or output-root deletion is authorized.

### 6. Publish terminal record 448

On every terminal outcome Hermes publishes
`research/sprint_004/448_CEX002_HOURLY_KLINE_INTEGRATION_AND_REAL_RUN_RECORD.md` plus the matching
CURRENT_TASK and CEX-002 changes, commits and pushes only those three governance/evidence paths, and
returns both actor fields to the reviewer.

For status zero, record 448 must include the exact command, start/end/runtime, stdout, source commit,
both completion paths/hashes, source/byte/partition/row/gap totals, output byte totals, descriptor
rehash, every descriptor-referenced Parquet/lineage rehash, schema equality, row reconciliation,
and `.staging` contents. It must distinguish product completion from reviewer acceptance.

For any nonzero status, interruption, harness loss, or missing terminal evidence, record 448 must
preserve the exact error/log/process/output facts without guessing a cause. Partial hidden artifacts
remain untouched. No retry or cleanup follows.

## Prohibitions

No source/test/CLI correction, additional command, acquisition, network data call, recovery input,
V3 manifest, output repair, cleanup, catalog transaction, NautilusTrader work, experiment, backtest,
model, Harmonic Trader repository work, PAPER, LIVE, next product, or next ticket is authorized.
Gate 2 remains accepted; Gate 3 and CEX-002 remain `IN_PROGRESS`; next ticket remains `NONE`.

## Reviewer publication scope

Under the AGENTS.md reviewer governance-publication exception this review commits and pushes
exactly:

- `research/sprint_004/447_CEX002_HOURLY_KLINE_SOURCE_ACCEPTANCE_AND_REAL_RUN.md`;
- `docs/handoff/CURRENT_TASK.md`; and
- `tickets/CEX-002.md`.

The accepted three-path source drop remains untracked for Hermes integration. All data and unrelated
dirty paths remain unstaged and untouched.
