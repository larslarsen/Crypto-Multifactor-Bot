# REVIEW-0150 — UNIVERSE-001 SOURCE REJECTED

**Ticket:** UNIVERSE-001 — CoinGecko Survivorship-Free Universe Provider
**Status:** REJECTED
**Date:** 2026-07-22
**Next required actor:** Reviewer (decision required)
**Next ticket authorized:** NONE

## Findings

1. **P0 — Free API infeasible:** CoinGecko Demo/free tier restricts inactive-coin access. Required active+inactive fetch cannot work free.
2. **P0 — No historical dates:** Free API returns snapshot-only membership. No listing/delisting dates. Historical universe reconstruction impossible.
3. **P0 — Catalog incompatibility:** Published coingecko_universe datasets cannot be read by CatalogAsOfStore (market bars/reference only).
4. **P1 — Layer violation:** Network access in universe layer violates NETWORK_ALLOWED boundary.

## Decision

REJECT source. No source-only correction can satisfy the ticket using the free API.

## Reviewer options

A) Prospective free snapshots only
B) Paid historical source ($129/mo CoinGecko Analyst)
C) Bounded non-survivorship-free universe (BAR-001 instruments)

No next ticket authorized. Stop after push.
