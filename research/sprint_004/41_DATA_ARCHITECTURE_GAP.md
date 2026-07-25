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

The `UniverseBinding` protocol, `CMCSurvivorshipBinding` adapter, and
`FactorDrivenPaperLoop` binding integration are now in `src/`. The static
`universe = list(PAPER_TO_INSTRUMENT_ID.keys())` pattern is removed from all
paper scripts. All 11 paper/experiment entrypoints load the binding from a
catalog-published CMC survivorship dataset and fail closed if the dataset is
missing or empty.

## Next tickets (see ADR-0014)

UNIVERSE-006 → DATA-011 → EXP-009; park DATA-010 / draft UNIVERSE-005 / DEX-003 behind that spine.
