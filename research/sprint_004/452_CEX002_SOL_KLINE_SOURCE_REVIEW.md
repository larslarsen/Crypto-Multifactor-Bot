# CEX-002 Review 452 - Sol Kline Source Review

- **Date:** 2026-09-02
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** accept the production correction and require one literal test-fixture correction
- **Gate 2:** `ACCEPTED`
- **Gate 3:** `IN_PROGRESS`
- **Next required actor:** Sr Dev - Codex Sol, High
- **Next ticket:** `NONE`

## Decision

The ADR-0035 production correction is accepted at:

```text
src/cryptofactors/ingest/binance_usdm_klines.py
sha256 = cfefdd2694bb76722d3b84da00444b8cafe5eec5a323b6ca4b57a3c3f6abd1a9
lines  = 1,239
```

Static inspection confirms that it uses exact scaled-integer volume comparisons, keeps the raw
timeline for duplicate and missing-hour validation, applies the 40/67 product-specific exclusions,
records one typed gap and raw lineage entry per exclusion, preserves the physical/excluded/product
equations, advances the lineage and completion versions, keeps the accepted schemas unchanged, and
leaves old content-addressed artifacts untouched. The CLI remains byte-identical at SHA-256
`f1a4df5065de841f15d1bbbb1692b98bf97a010c37f7294f9230d0c02d240542` and 49 lines.

The complete two-path drop is not yet accepted because the one authorized focused command stopped
with 53 passing cases and one failing case. The failure is confined to
`test_product_scoped_volume_exclusions_have_exact_gaps_lineage_and_equations`. Its fourth fixture
uses the helper's exact low price `90.000000000000000003`, taker-buy base volume `11`, and taker-buy
quote volume `990`. The exact lower bound is `990.000000000000000033`, so the production code
correctly reports the taker-buy pair itself as inconsistent. The test intended to isolate only the
taker-buy-within-total failure and its expected flags are therefore incompatible with its input.

## Exact correction authorization

Sr Dev - Codex Sol High is authorized to edit only
`tests/ingest/test_binance_usdm_klines.py` at the reviewed SHA-256
`526c7d42f92ce9c6c866f86279a2917d62ce15efd6cef8cc46945d5bbe1cf7fb`. In the fourth source row of
the product-scoped exclusion test, change only:

```text
buy_quote_volume="990"
```

to:

```text
buy_quote_volume="1000"
```

That value is inside the exact candle-price bounds for taker-buy base volume 11 and does not exceed
total quote volume 1000. The row then isolates the intended base-volume-within-total failure. No
expected result, production source, CLI, or other test may change.

Under the targeted senior exception, Sol may then run exactly once:

```text
PYTHONPATH=src .venv/bin/python -m pytest tests/ingest/test_binance_usdm_klines.py -q --tb=short
```

Sol stops after reporting the exact command/output, hashes, and line counts. It performs no real-data
run, data/output mutation, integration, repository-record edit, Git operation, network action,
cleanup, acquisition, catalog transaction, NautilusTrader work, experiment, model, Harmonic Trader
repository work, other product, or next-ticket work. Hermes remains unauthorized pending reviewer
inspection.

## Reviewer publication scope

The reviewer publishes exactly this review, `docs/handoff/CURRENT_TASK.md`, and `tickets/CEX-002.md`.
All source, test, CLI, data, hidden output, and unrelated dirty paths remain unstaged and untouched.
