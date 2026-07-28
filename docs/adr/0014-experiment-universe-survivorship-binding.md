# ADR 0014 — Experiment & Paper Must Bind Survivorship-Aware Universe

- **Status:** Accepted (REVIEW-0249)
- **Date:** 2026-07-24
- **Supersedes in part:** implicit practice of hardcoded `PAPER_TO_INSTRUMENT_ID` as experiment universe

## Context

1. **CMC CEX survivorship backfill (UNIVERSE-003) now exists** at
   `data/survivorship/cmc_dead_universe_full.csv` (**1,756** inactive coins with birth +
   death-proxy dates, Aware-level per ADR-0012). Earlier runs produced a stub (~1 row);
   the full backfill completed **after** EXP-004…EXP-008 / PAPER-007…PAPER-009.

2. **All prior TSMOM grid, OOS, full-window, and paper sessions used a fixed static map**
   (`PAPER_TO_INSTRUMENT_ID` — 10 or 23 liquid names). They did **not** call
   `CMCSurvivorshipProvider.universe_at(t)`. Promotion metadata sometimes *named*
   `cmc_survivorship_universe` / `coingecko_universe` without consuming membership.

3. **Consequence:** those experiments are **invalid for any claim that depends on
   survivorship-free (or even survivorship-aware) universe construction**. They remain
   useful only as engineering smoke tests. Combined with EXP-008 (multiple-testing false
   discovery on `tsmom_14_3`), **no research candidate is scientifically live-eligible**.

4. **Data inventory vs consumption gap (2026-07-24):**

   | Asset | Collected? | Consumed by exp/paper? |
   |-------|------------|------------------------|
   | Binance spot bars (U50 / 52-symbol expansion) | Partial–yes | Paper uses ≤23 static IDs; cleared path often 10 |
   | BitMEX funding (45 perps) | Yes | Not in TSMOM path |
   | CMC dead-coin registry (1,756) | Yes (CSV) | **No** — not catalog-published as runtime universe; not in loop |
   | DEX pool OHLCV (DATA-010 partial) | Partial | **No** |
   | Birdeye listings queue (UNIVERSE-004) | Yes | **No** OHLCV/bars path |

5. Draft mega-tickets (UNIVERSE-005 ~2.7k CEX pairs, DEX-003 survivorship) expand
   *collection* without fixing the **binding** failure. Collection without binding repeats
   the invalid-experiment problem at larger scale.

## Decision

1. **Hard gate — UniverseBinding contract**
   - Every experiment and paper session MUST resolve membership via
     `universe_at(decision_time) -> frozenset[instrument_id]` from a **catalog-published**
     universe dataset (not a hardcoded dict of “who we like”).
   - Static maps (`PAPER_TO_*`) remain **venue/symbol translation only**, never membership.
   - Run fingerprint MUST include `universe_dataset_id` + `universe_code_version`.
   - Missing, empty, or unpublished universe → **fail closed** (no scores, no paper fills).

2. **Survivorship policy for CEX research (Aware-level)**
   - Membership at `t` = instruments with `birth_date <= t` and
     (`death_proxy_date is null` OR `death_proxy_date > t`), labeled proxy per ADR-0012.
   - **Tradable research panel** = survivorship membership ∩ instruments with quality
     bars available as-of `t` ∩ optional liquidity screen (declared in experiment spec).
   - Dead coins without bars still affect **denominator / eligibility history** where the
     factor requires full-universe ranks; factors that need prices omit missing names
     but must log coverage ratio.

3. **Scientific invalidation of prior runs**
   - EXP-004 through EXP-008, PAPER-007 through PAPER-009, and related grid/paper
     artifacts are marked **`survivorship_invalid: true`** for research conclusions.
   - They do not authorize promotion. Re-run only under pre-registration (ARCH-001)
     **after** UniverseBinding is live.

4. **Phased work order (collection subordinate to binding)**

   | Order | Ticket | Purpose |
   |------:|--------|---------|
   | 1 | **ARCH-002** | UniverseBinding interface + fail-closed experiment/paper wiring |
   | 2 | **UNIVERSE-006** | Publish CMC CSV → catalog universe dataset; `universe_at` production path |
   | 3 | **DATA-011** | Rebuild quality-cleared CEX bar panel for binding-eligible symbols (Binance first) |
   | 4 | **EXP-009** | Pre-registered single hypothesis on bound universe (no grid fishing) |
   | 5 | **DEX-003** | DEX birth/death metadata (after CEX path honest) |
   | 6 | **DATA-010** rework | Finish DEX OHLCV only if DEX factors are in scope |
   | 7 | **UNIVERSE-005** | Split later: Binance-full → other CEX; not 2.7k pairs in one ticket |

5. **Reject for now:** treating UNIVERSE-005 or further raw expansion as the next active
   ticket while experiments still ignore survivorship.

## Consequences

- Research velocity slows until binding ships — correct tradeoff.
- Jr/Sr cannot “accept” experiment tickets that hardcode membership.
- CMC Aware-level limits claims: no final-price/failure-cause authority (ADR-0012).
- Paper trading on static 10-name maps is ops-only until DATA-011 + binding land.
