# 41 — Data Architecture Gap: Collection vs Consumption

**As of:** 2026-07-24  
**Governing ADR:** `docs/adr/0014-experiment-universe-survivorship-binding.md`

## Executive finding

We now **have** a CEX dead-coin survivorship registry (1,756 rows). We **ran all material
TSMOM experiments before that registry existed / was complete**. Those experiments used a
**static liquid-name map**, not `universe_at(t)`. Therefore:

> **Prior experiment and paper results are invalid for survivorship-aware research claims.**

(They were already non-live-eligible via EXP-008 multiple-testing failure on `tsmom_14_3`.)

## What Jr collected

| Artifact | Rows / scale | Path |
|----------|--------------|------|
| CMC inactive map + detail | **1,756** coins | `data/survivorship/cmc_dead_universe_full.csv` |
| Binance expansion bars | 52 symbols | `canonical_universe_expansion` staged |
| Quality-cleared paper bars | **10** symbols | PASS dataset used by PAPER-009 |
| BitMEX funding | 45 perps | DATA-009 evidence |
| DEX OHLCV | ~15 symbols with data | DATA-010 partial / BLOCKED |
| Birdeye screen queue | 14 survivors | UNIVERSE-004 |

## What experiments actually use

**BANNED** as of ARCH-002:

```text
universe = list(PAPER_TO_INSTRUMENT_ID.keys())   # static 10–23 names
# NOT: CMCSurvivorshipProvider.universe_at(decision_time)
```

Scripts must now load a `UniverseBinding` from the catalog. `PAPER_TO_INSTRUMENT_ID`
remains a symbol-translation map only, never a membership source.

Promotion rows may list `universe_ids=("cmc_survivorship_universe",)` as **labels only**.

## Invalidation list (research conclusions)

Mark as `survivorship_invalid` for any scientific / promotion use:

- EXP-004 grid, EXP-005 OOS, EXP-006 extended OOS, EXP-007 full-window, EXP-008 MTC  
- PAPER-007, PAPER-008, PAPER-009  
- PROMO-003 chain (already archived false discovery; survivorship is additional defect)

Engineering value retained: pipeline smoke, risk-limit wiring, catalog publish paths.

## Free data we still need (minimal honest set)

**Must have before next real experiment:**

1. Catalog-published survivorship universe + `universe_at(t)` in the paper loop  
2. Quality bars for the **intersection** of (alive at t) ∩ (mapped venue symbol) ∩ screen  
3. Explicit coverage metrics (eligible N, scored N, missing bars N) per decision date  
4. Funding series only if the pre-registered factor needs it (TSMOM spot may not)

**Nice later (not blocking binding):**

- Full Binance USDT history with exchange-native birth = first bar  
- DEX birth/death (DEX-003) + OHLCV (DATA-010) for DEX factors  
- MEXC/Kraken/Blofin (UNIVERSE-005 split)  

## Anti-patterns observed

1. **Expand then ignore** — DATA-008 52 symbols collected; paper still 10.  
2. **Label without bind** — universe_ids in promotion ≠ runtime membership.  
3. **Mega-tickets** — UNIVERSE-005 (~2.7k pairs) before binding works.  
4. **Accept without review** — expansion tickets Jr-accepted; REVIEW-0211/0212 still open.

## Required architecture shape

```text
decision_time t
    → UniverseBinding.universe_at(t)     # catalog dataset, fail-closed
    → BarStore.panel(ids, t)             # quality-cleared only
    → optional LiquidityScreen
    → Factor.scores(eligible_ids, t)
    → Allocator → PaperBroker
    → artifact fingerprint includes universe_dataset_id
```

## Status update: ARCH-002 landed

The `UniverseBinding` protocol and `FactorDrivenPaperLoop` binding integration
are in `src/`. The static `universe = list(PAPER_TO_INSTRUMENT_ID.keys())`
pattern is removed from all paper scripts. All 11 paper/experiment entrypoints
load the binding from catalog-published datasets and fail closed if either is
missing, empty, or does not cover the decision time.

### REVIEW-0249 rework — membership semantics corrected

The first pass inverted membership: it treated the CMC dead-coin graveyard as
the research universe, so liquid names (absent from the graveyard) were never
members and the panel went empty at recent decision times. Membership is now:

```
universe(t) = quality_bar_panel_with_coverage(t)  minus  cmc_dead_at(t)
```

- The panel comes from the accepted DATA-011 artifact
  `ds_2bf3bf42…`, read from published bars. `PAPER_TO_INSTRUMENT_ID` is used
  only to render numeric instrument ids as paper symbols — translation, never
  membership. `PAPER_PANEL_SYMBOLS` and `CMCSurvivorshipBinding` were removed
  because both were static/dead-list membership paths.
- Names are excluded only when the CMC record agrees on **both** ticker and
  coin name, so the SOL/UNI/CRV/OP collisions no longer drop live names.
- Run artifacts fingerprint `universe_dataset_id` **and**
  `bar_panel_dataset_id`, plus policy `quality_bar_panel_minus_cmc_dead_v1`,
  code version `v3`, decision time, and coverage counts.

Two latent defects were found and fixed during this rework: the catalog loader
read a non-existent `relative_path` column instead of `storage_uri` (so it had
never resolved a real published dataset), and `period_start` was read as epoch
seconds when `market_bars` stores microseconds.

**Known data gap:** DATA-011 carries bars for 22 of the 23 mapped paper
symbols — `DOGEUSD` (instrument 11) has no bars in either the `daily/` or
`intraday/` tree, so the bound panel is 22. This contradicts REVIEW-0216's
"all 23 paper symbols backfilled, 0 excluded" and is recorded here for the
reviewer; ARCH-002 correctly excludes it rather than inventing coverage.

## Next tickets (see ADR-0014)

UNIVERSE-006 → DATA-011 → EXP-009; park DATA-010 / draft UNIVERSE-005 / DEX-003 behind that spine.
