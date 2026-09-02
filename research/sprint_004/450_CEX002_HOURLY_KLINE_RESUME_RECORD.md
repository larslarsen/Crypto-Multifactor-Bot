# CEX-002 Record 450 — Hourly Kline Resume Record

- **Date:** 2026-09-02
- **Ticket:** CEX-002
- **Decision:** resume exited 1 with a normalizer exception after ~1,500 seconds; partial artifacts preserved untouched
- **Gate 2:** `ACCEPTED`
- **Gate 3:** `IN_PROGRESS`
- **Next required actor:** Lead Quantitative Finance Researcher/Engineer
- **Next ticket:** `NONE`

## Preproof (all passed)

- `HEAD == origin/main == 0c908661738e4a21f308514d856b7aebe375fff5`
- Source `src/cryptofactors/ingest/binance_usdm_klines.py` SHA-256 `d553e5aea9d58f0bd80ef39e5ab9d1bc6a7e566e2ac8aacaf66b81f36eb8ddd4` (1,042 lines)
- CLI `scripts/research/normalize_binance_usdm_klines.py` SHA-256 `f1a4df5065de841f15d1bbbb1692b98bf97a010c37f7294f9230d0c02d240542` (49 lines)
- `data/.cex002_bar_1h`: 6,787 Parquets + 6,787 lineages, empty `.staging`, no completion/gap artifact
- `data/.cex002_trade_flow_1h`: 6,787 Parquets + 6,787 lineages, empty `.staging`, no completion/gap artifact
- No running `normalize_binance_usdm_klines.py` process
- Available bytes: 41,509,740 (above 33,566,545,257 floor)

## Real run — terminal evidence

Hermes ran exactly one identical foreground command from the repository root and remained attached to the unified execution session until terminal:

```text
PYTHONPATH=src .venv/bin/python scripts/research/normalize_binance_usdm_klines.py \
  --generation0-state data/cex002_qualify/gate2/state.sqlite \
  --generation0-content-root data/cex002_qualify/gate2/content \
  --bar-output-root data/.cex002_bar_1h \
  --trade-flow-output-root data/.cex002_trade_flow_1h
```

- **End:** 2026-09-02T05:41:44Z
- **Runtime:** ~1,500 seconds (~25 minutes)
- **Exit code:** 1
- **Exception:** `cryptofactors.ingest.binance_usdm_klines.KlineNormalizationError: taker-buy base volume exceeds total`
- **Exception location:** `src/cryptofactors/ingest/binance_usdm_klines.py:656` in `_parse_kline_row`, called from `_iter_kline_rows` (line 707), `_normalize_sources` (line 877), `_normalize_with_roots` (line 1026), `normalize_from_generation0` (line 1039)
- **Process status at observation:** absent from `ps aux`
- **No retry, wrapper, detach, polling loop, signal, cleanup, or output-root deletion was performed.**

## Partial hidden artifacts (untouched)

The conversion was interrupted before publishing completion descriptors. The partial state is preserved exactly as left:

- `data/.cex002_bar_1h/.partitions/` — 20,335 Parquet files (693 symbol dirs)
- `data/.cex002_bar_1h/.lineage/` — 20,335 lineage JSON files
- `data/.cex002_trade_flow_1h/.partitions/` — 20,335 Parquet files (693 symbol dirs)
- `data/.cex002_trade_flow_1h/.lineage/` — 20,335 lineage JSON files
- `data/.cex002_bar_1h/.staging/` — empty
- `data/.cex002_trade_flow_1h/.staging/` — empty
- Completion descriptors: none
- Gap artifacts: none observed
- Output byte totals at observation:
  - `data/.cex002_bar_1h`: 919,836,209 bytes
  - `data/.cex002_trade_flow_1h`: 1,435,638,751 bytes
- Filesystem available bytes at observation: 37,658,760

## Provenance note

The accepted generation-0 authority (`data/cex002_qualify/gate2/state.sqlite`, `data/cex002_qualify/gate2/content`) was not altered. This command downloads nothing. No source/test/CLI correction, additional command, acquisition, network call, recovery input, V3 manifest, output repair, cleanup, catalog transaction, NautilusTrader work, experiment, backtest, model, Harmonic Trader work, PAPER, LIVE, next product, or next ticket was performed.

## Actor fields

Both actor fields return to the Lead Quantitative Finance Researcher/Engineer. Gate 2 remains `ACCEPTED`; Gate 3 and CEX-002 remain `IN_PROGRESS`; next ticket remains `NONE`.
