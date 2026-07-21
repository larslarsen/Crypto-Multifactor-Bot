# 13 — Research Lead Decisions (Sprint 003 Source Feasibility)

**Ticket:** AUD-003
**Accepted evidence commit:** `8b61fb81a9f997f8c45481a5d95f257443c32c4f`
**Audit record:** `research/sprint_003/12_AUDIT_EXECUTION.md`
**Acceptance record:** `docs/reviews/REVIEW-0008_AUD-003_FINAL.md`

These are the Research Lead's source-acceptance decisions derived from the
Sprint 003 audit. They are recorded verbatim from the audit acceptance and do
not constitute research conclusions on strategy performance.

## Per-provider decisions

| Provider | Decision |
| --- | --- |
| Binance | `ACCEPT — BACKFILL_PRIMARY` |
| Bybit | `CONDITIONAL — CROSSCHECK` and incremental derivatives/funding |
| Coin Metrics Community | `CONDITIONAL — EXPLORATORY_PHASE2` |
| OKX | `DEFER` historical approval pending audited historical files |
| Kraken | `DEFER` pending successful bulk-file acquisition |
| DefiLlama | `CONDITIONAL — EXPLORATORY_PHASE2`; emissions access not established as free |
| Tokenomist / Messari | `DEFER` pending authorized access or vendor trial |
| CoinGecko / CoinMarketCap | discovery and cross-check only; not point-in-time authorities |
| DIL-01 | remains deferred |

## Mandatory Binance conditions

- Preserve provider checksums.
- Retain corrected and superseded objects rather than overwriting them.
- Infer and record timestamp units per object.
- Support both millisecond and microsecond archives.
- Never infer units from filename dates alone.

## Mandatory Bybit conditions

- Deterministic cursor pagination.
- Raw-page retention.
- Exact preservation of fractional-second timestamps.
- Source-specific schema/version records.

## Transparency note

Partial and failed audit checks were preserved transparently in the audit outputs
and do not block acceptance:

- `binance_precision_comparison.json` (native `compare_binance_archive_precision`)
  remains `FAILED` — the toolkit requires `has_header=True` and Binance daily dumps
  are headerless. The runner-level adapter (`binance_precision_comparison_adapter.json`)
  supplies the equivalent evidence (ms→us transition supported).
- `bar_reconstruction_comparison.json` now completes with explicit comparable
  dimensions (OHLC + base/quote volume) while marking `trade_count` as not
  comparable. Binance kline provider trade count exists, but it is not equivalent
  to aggTrades archive record count and is never relabeled as such.

Both toolkit limitations are recorded as backlog defects: `AUD-004` (headerless
precision comparator) and `AUD-005` (provider-candle comparison without optional
fields). AUD-005 closes the optional-field comparison gap by explicit exclusion,
and neither blocks RAW-001.
