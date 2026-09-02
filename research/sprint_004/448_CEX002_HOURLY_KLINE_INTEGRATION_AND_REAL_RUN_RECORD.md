# CEX-002 Record 448 — Hourly Kline Integration and Real Run Record

- **Date:** 2026-09-02
- **Ticket:** CEX-002
- **Decision:** integration accepted, real run interrupted by harness timeout; partial artifacts preserved untouched
- **Gate 2:** `ACCEPTED`
- **Gate 3:** `IN_PROGRESS`
- **Next required actor:** Lead Quantitative Finance Researcher/Engineer
- **Next ticket:** `NONE`

## Source integration

Jr Dev — Hermes executed Review 447's exact ordered workflow. The three accepted paths were reproved at their exact hashes and line counts:

| path | SHA-256 | lines |
|---|---|---:|
| `src/cryptofactors/ingest/binance_usdm_klines.py` | `d553e5aea9d58f0bd80ef39e5ab9d1bc6a7e566e2ac8aacaf66b81f36eb8ddd4` | 1,042 |
| `scripts/research/normalize_binance_usdm_klines.py` | `f1a4df5065de841f15d1bbbb1692b98bf97a010c37f7294f9230d0c02d240542` | 49 |
| `tests/ingest/test_binance_usdm_klines.py` | `b95d16614063043fe9a0d3eeb0e0cf63e9196b05c7e26f18cbd94162cb510a2a` | 482 |

The three focused checks passed in order: pytest (43/43), ruff (`All checks passed!`), `check_repo_control.py`. The three paths were staged, verified exact, committed as `f9613e2b74a7eb9933271073f3bf8a4c99a676fe` ("CEX-002: integrate hourly kline source/test drop (Review 447)"), and pushed. `HEAD == origin/main == f9613e2b74a7eb9933271073f3bf8a4c99a676fe`.

## Capacity and destination preproof

Immediately before the real command, filesystem available bytes on `data/` were 45,435,129,856, above the protected Review-446 floor of 33,566,545,257. Both `data/.cex002_bar_1h` and `data/.cex002_trade_flow_1h` were absent and not symlinks.

## Real run — terminal evidence

Hermes ran exactly one foreground local invocation from the repository root and remained attached until terminal:

```text
PYTHONPATH=src .venv/bin/python scripts/research/normalize_binance_usdm_klines.py \
  --generation0-state data/cex002_qualify/gate2/state.sqlite \
  --generation0-content-root data/cex002_qualify/gate2/content \
  --bar-output-root data/.cex002_bar_1h \
  --trade-flow-output-root data/.cex002_trade_flow_1h
```

- **Start:** 2026-09-02T04:36:15Z
- **End:** 2026-09-02T04:46:15Z (harness timeout at 600 s)
- **Runtime:** 600 seconds
- **Exit code:** 124 (timeout)
- **Process status at observation:** 0 `normalize_binance_usdm_klines.py` processes running; the process is not present in `ps aux`.
- **stdout:** none captured (the harness returned only the timeout signal).
- **No retry, wrapper, detach, polling loop, signal, cleanup, or output-root deletion was performed.**

## Partial hidden artifacts (untouched)

The conversion was interrupted before publishing completion descriptors. The partial state is preserved exactly as left:

- `data/.cex002_bar_1h/.partitions/` — 6,787 Parquet files
- `data/.cex002_bar_1h/.lineage/` — 6,787 lineage JSON files
- `data/.cex002_trade_flow_1h/.partitions/` — 6,787 Parquet files
- `data/.cex002_trade_flow_1h/.lineage/` — 6,787 lineage JSON files
- `data/.cex002_bar_1h/.staging/` — empty
- `data/.cex002_trade_flow_1h/.staging/` — empty
- Completion descriptors: none (no `*.descriptor`, `*.completion`, or `*.log` file in either root)
- Gap artifacts: none observed
- Output byte totals at observation:
  - `data/.cex002_bar_1h`: 308,044,131 bytes
  - `data/.cex002_trade_flow_1h`: 481,115,217 bytes
- Filesystem available bytes at observation: 43,601,747,968

## Provenance note

The accepted generation-0 authority (`data/cex002_qualify/gate2/state.sqlite`, `data/cex002_qualify/gate2/content`) was not altered. This command downloads nothing. No source/test/CLI correction, additional command, acquisition, network call, recovery input, V3 manifest, output repair, cleanup, catalog transaction, NautilusTrader work, experiment, backtest, model, Harmonic Trader work, PAPER, LIVE, next product, or next ticket was performed.

## Actor fields

Both actor fields return to the Lead Quantitative Finance Researcher/Engineer. Gate 2 remains `ACCEPTED`; Gate 3 and CEX-002 remain `IN_PROGRESS`; next ticket remains `NONE`.
