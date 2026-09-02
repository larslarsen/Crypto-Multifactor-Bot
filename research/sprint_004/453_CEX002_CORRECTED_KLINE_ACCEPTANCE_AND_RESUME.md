# CEX-002 Review 453 - Corrected Kline Acceptance and Resume

- **Date:** 2026-09-02
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** accept the corrected source/test drop and authorize Hermes integration plus one resume
- **Gate 2:** `ACCEPTED`
- **Gate 3:** `IN_PROGRESS`
- **Next required actor:** Jr Dev - Hermes
- **Next ticket:** `NONE`

## Source acceptance

Review 453 accepts the complete ADR-0035 drop at these exact identities:

| path | SHA-256 | lines |
|---|---|---:|
| `src/cryptofactors/ingest/binance_usdm_klines.py` | `cfefdd2694bb76722d3b84da00444b8cafe5eec5a323b6ca4b57a3c3f6abd1a9` | 1,239 |
| `tests/ingest/test_binance_usdm_klines.py` | `ee42242d2c5e766ad6bd9ad4a0040c4344ae6b8b61d0088273265d488d5881d4` | 817 |

The already-integrated CLI remains byte-identical:

| path | SHA-256 | lines |
|---|---|---:|
| `scripts/research/normalize_binance_usdm_klines.py` | `f1a4df5065de841f15d1bbbb1692b98bf97a010c37f7294f9230d0c02d240542` | 49 |

Sol made only Review 452's literal test-fixture correction. Replacing line 269's new
`buy_quote_volume="1000"` with the prior `"990"` in the byte stream reproduces the reviewed prior
test SHA-256 `526c7d42f92ce9c6c866f86279a2917d62ce15efd6cef8cc46945d5bbe1cf7fb` exactly. Production and
expected results did not change.

Sol then ran the one authorized command exactly once:

```text
PYTHONPATH=src .venv/bin/python -m pytest tests/ingest/test_binance_usdm_klines.py -q --tb=short
......................................................                   [100%]
```

It exited zero with 32 test functions and 54 collected/passing cases. Sol performed no real-data,
output, Git, record, integration, network, cleanup, acquisition, or other work.

Review 452's production inspection remains accepted: exact volume arithmetic, raw-timeline
validation, product-scoped exclusions, typed gaps, source-bound exclusion lineage, corrected
equations and constants, versioned completion/lineage, unchanged product schemas, and immutable
content-addressed resume all match ADR-0035. Gate 3 is not accepted until the corrected real products
complete and are reconciled.

## Fixed integration and resume pre-state

At this review:

- `HEAD == origin/main == b47f46a603956c0541364054395ffdc50491f6dc`;
- each hidden product root contains 20,335 Parquets and 20,335 lineage JSON documents;
- both `.staging/` directories are empty;
- neither product has a completion, quality-gap, or quality-gap-lineage artifact;
- no real kline normalizer is running; and
- available bytes are 35,803,824,128, above the unchanged 33,566,545,257-byte preflight floor.

The accepted generation-0 authority is unchanged. The partial hidden artifacts remain unaccepted
and must not be deleted or cleaned. The untracked `run_continuation_runner.sh` must not be read,
edited, staged, invoked, or otherwise used.

## Hermes authorization

Jr Dev - Hermes performs only this ordered workflow.

### 1. Reprove and test the exact drop

Hermes verifies `HEAD == origin/main`, the three exact hashes and line counts above, and the exact
partial-output state. It runs these commands in order and stops on the first nonzero status:

```text
PYTHONPATH=src .venv/bin/python -m pytest tests/ingest/test_binance_usdm_klines.py -q --tb=short
PYTHONPATH=src .venv/bin/python -m ruff check --no-cache src/cryptofactors/ingest/binance_usdm_klines.py scripts/research/normalize_binance_usdm_klines.py tests/ingest/test_binance_usdm_klines.py
python3 scripts/check_repo_control.py
```

No full suite is authorized at this intermediate product boundary.

### 2. Integrate exactly two paths

Hermes stages only the accepted source and test paths, verifies the cached path set is exact, runs
`git diff --cached --check`, commits with a CEX-002 corrected-kline integration message, pushes, and
proves `HEAD == origin/main`. No unrelated path or CLI may be staged. The accepted hashes must remain
exact after commit.

### 3. Reprove the resume preconditions

Immediately before launch, Hermes reproves the exact 20,335/20,335 Parquet/lineage counts in both
roots, empty staging, absent completion and gap artifacts, no live real kline normalizer, and at
least 33,566,545,257 available bytes. It confirms its unified foreground execution mechanism can
remain attached and observable for at least 3,600 seconds. Any mismatch or shorter execution ceiling
stops without launch.

### 4. Run one corrected foreground resume

Hermes runs exactly one invocation from the repository root:

```text
PYTHONPATH=src .venv/bin/python scripts/research/normalize_binance_usdm_klines.py \
  --generation0-state data/cex002_qualify/gate2/state.sqlite \
  --generation0-content-root data/cex002_qualify/gate2/content \
  --bar-output-root data/.cex002_bar_1h \
  --trade-flow-output-root data/.cex002_trade_flow_1h
```

Hermes remains attached to that unified session until terminal, with a 3,600-second allowance. A
yielded tool session may be waited on without relaunch. There is no wrapper, detach, PID polling
loop, second invocation, retry, signal, cleanup, output deletion, acquisition, or network action.
The command downloads nothing.

### 5. Publish terminal Record 454

On every terminal outcome Hermes publishes
`research/sprint_004/454_CEX002_CORRECTED_KLINE_RESUME_RECORD.md` plus matching CURRENT_TASK and
CEX-002 changes, commits and pushes only those three evidence/control paths, and returns both actor
fields to the reviewer.

For status zero, Record 454 includes exact start/end/runtime/stdout, source commit, completion
paths/hashes, source/byte/partition/row/exclusion/gap totals, invariant-failure totals, output bytes,
staging contents, and complete descriptor-referenced Parquet/lineage/schema/digest reconciliation.
It explicitly proves the product equations 16,033,509 - 40 = 16,033,469 and
16,033,509 - 67 = 16,033,442. Product completion is not reviewer acceptance.

For any nonzero status or lost terminal evidence, Record 454 records the exact facts and stops
without guessing, retry, or cleanup.

## Prohibitions

No source/test/CLI edit, new code, acquisition, redownload, network call, wrapper, cleanup, catalog
transaction, NautilusTrader work, experiment, backtest, model, Harmonic Trader repository work,
other product, PAPER, LIVE, or next ticket is authorized. Gate 2 remains accepted; Gate 3 and
CEX-002 remain `IN_PROGRESS`; next ticket remains `NONE`.

## Reviewer publication scope

The reviewer publishes exactly this review, `docs/handoff/CURRENT_TASK.md`, and `tickets/CEX-002.md`.
The accepted source/test drop remains unstaged for Hermes integration. All data, runner, and
unrelated dirty paths remain unstaged and untouched.
