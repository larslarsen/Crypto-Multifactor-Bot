# CURRENT_TASK

Ticket: UNIVERSE-001
State: BLOCKED
Next required actor: Reviewer (decision required)
Next ticket authorized: NONE

Sr source rejected (not yet reviewed by strong engineering model). P0 findings:
1. CoinGecko free tier restricts inactive-coin access — required active+inactive fetch infeasible free.
2. No listing/delisting dates in free API — historical membership reconstruction impossible.
3. Published coingecko_universe dataset incompatible with CatalogAsOfStore (market bars/reference only).
4. Network access in universe layer violates NETWORK_ALLOWED boundary.

Governing documents:
- tickets/UNIVERSE-001.md (BLOCKED)
- docs/reviews/REVIEW-0149_UNIVERSE-001_AUTHORIZED.md
- docs/reviews/REVIEW-0150_UNIVERSE-001_REJECTED.md

## Reviewer decision required

Three options for unblocking universe construction:

A) **Prospective free snapshots only** — accept current free API, accumulate snapshots forward. No historical universe reconstruction. Bounded by what we can capture from today.

B) **Paid historical source** — use CoinGecko Analyst ($129/mo) or similar for full historical universe. Requires budget decision.

C) **Bounded non-survivorship-free universe** — use current BAR-001 instruments for experiments. Accept survivorship bias for initial research. Fastest path to functionality.

No next ticket authorized. No further work on UNIVERSE-001 until Reviewer selects option.

## Stop condition

Reviewer selects option, updates ticket status, authorizes next work. No commits until decision.
