# REVIEW-0235 - DEX-002 REWORK AUTHORIZED

**Ticket:** DEX-002 - Screened Free DEX OHLCV Acquisition
**Decision:** AUTHORIZED
**Reviewer:** Lead Quantitative Finance Researcher/Engineer
**Date:** 2026-07-26

## Selection

DEX-002 is the next P0 ticket. DATA-007 is accepted and supplies the provider
capability evidence on which DEX-002 depends. DATA-008 and DATA-009 remain P1 and
are not authorized.

## Architectural ruling

The prior DEX-002 design is not eligible for incremental patching:

- DexScreener snapshots were converted into synthetic OHLCV candles despite
  DATA-007 classifying DexScreener as pool statistics only.
- screening could pass on null metrics or context-only evidence;
- failed/empty providers could advance watermarks and become permanently abandoned;
- incremental deltas could replace full canonical history;
- published data had no raw-response dependencies.

The rewritten ticket is the sole governing specification. GeckoTerminal is the only
current OHLCV authority; DexScreener screens; DefiLlama is context only. No provider
may exceed its evidenced capability.

## Routing

Because this ticket changes acquisition identity, lineage, canonical snapshot
semantics, and quantitative bar validity, use Claude Opus 5 for the Sr source pass.
Use Claude Opus 5 again in the separate Jr integration/test role; role separation is
preserved even though the same model family is selected for reliability.

## Constraints

- No work on DATA-008, DATA-009, DEX-003, or factor research.
- No Birdeye OHLCV, paid source, synthetic bar, or LIVE authority.
- Do not overwrite or reinterpret the old report as accepted evidence.

## Next

- **Next required actor:** Sr Dev - Claude Opus 5
- **Next ticket authorized:** NONE
