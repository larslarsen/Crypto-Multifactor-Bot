# REVIEW-0240 - DATA-008 REWORK AUTHORIZED

**Ticket:** DATA-008 - Free CEX Universe Expansion (Binance-first)
**Decision:** AUTHORIZED
**Reviewer:** Lead Quantitative Finance Researcher/Engineer
**Date:** 2026-07-26

## Selection

DATA-008 is the next ticket. It is P1, depends only on accepted DATA-006 and
DATA-007 work, and closes the existing Binance expansion correctness gap before
UNIVERSE-005 or new factor research can use the expanded CEX panel.

DATA-009, DEX-003, UNIVERSE-005, ARCH-002, and EXP-009 remain unauthorized.

## Rework authority

The prior DATA-008 acceptance was invalidated by REVIEW-0211. Retain useful fetch,
watermark, and allocator components, but do not treat the existing 52-symbol artifact
as accepted evidence.

The rework must:

1. Select only Binance spot symbols whose status and quote asset satisfy the ticket.
2. Parse leveraged-token suffixes from the base asset; never use substring matching
   that excludes ordinary symbols such as `TRUMP` because they contain `UP`.
3. Apply a versioned exclusion taxonomy for stablecoins, fiat, tokenized commodities,
   and other non-target bases. Every exclusion must carry a reason.
4. Rank deterministically from observed liquidity/volume evidence with explicit window,
   timestamp, tie-break, and raw lineage. Do not describe 24-hour ticker data as 30-day
   volume.
5. Separate discovery, eligibility, and priority. Newly listed or short-history assets
   must be documented rather than silently admitted as research-ready history.
6. Preserve exact acquisition responses before decoding and publish complete immutable
   lineage through the catalog.
7. Make incremental refresh retry-safe: failures retain prior watermarks, and a delta
   must never replace full canonical history as the latest dataset.
8. Publish a corrected report 36 with selected, excluded, failed, and deferred symbols;
   spans and row counts; rate-limit incidents; watermark changes; raw dependencies;
   and exact catalog reconciliation. `live_eligible` remains false.

## Routing

Use Claude Opus 5 for the Sr source pass. Use Claude Opus 5 again in the separate Jr
integration/test role because this ticket controls research-universe inputs and prior
weak tests did not protect its selection semantics.

## Constraints

- Binance public spot data only; no Bybit, Deribit, MEXC, Kraken, Blofin, paid plans,
  universe membership claims, factor research, paper promotion, or LIVE.
- No next ticket begins until reviewer acceptance.

## Next

- **Next required actor:** Sr Dev - Claude Opus 5
- **Next ticket authorized:** NONE
