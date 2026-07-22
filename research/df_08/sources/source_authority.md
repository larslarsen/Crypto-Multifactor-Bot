# Source authority note — Survivorship-free universe (DF-08 synthesis)

Synthesis target: whether accepted repository evidence authorizes construction of a
survivorship-free historical universe (complete listing/delisting events, final tradable
price, and failure cause per asset). Evidence synthesis only; no new factual inference.

## What is repository-native (used here)
Only accepted inventory, hashes, decisions, and prior accepted review findings are used.
The sixteen artifacts registered in `EVIDENCE_REGISTER.csv` span: sprint_002/06
(DF-08 question + reconstruction test), sprint_003/01, /02, /04, /08 (source decisions,
object inventory, PIT reference plan, research data decisions), REF-001 acceptance
(REVIEW-0017), the accepted REF-002 and REF-003 chains (tickets, reports, acceptance
reviews, decision matrices), and — for the preserved market-bar boundary only — BAR-001
(E15 tickets/BAR-001.md, E16 REVIEW-0042_BAR-001_ACCEPTED.md).

## Accepted substrate (must not be downgraded)
- REF-001 provides an accepted bitemporal identity/event-storage substrate only (G01 PASS).
- BAR-001 accepted canonical-bar authority: DF-08 does not downgrade it (E15/E16, preserved
  market-bar boundary only).
These are storage/identity substrates, not survivorship-free event authority.

## RD-06 exactly
Sprint-003 RD-06 recorded partial listing/delivery feasibility; its next action proposed an
instrument-master (launchTime/deliveryTime/state) plus last-trade polling. RD-06 did not
itself grant source or implementation authority. Later accepted REF-002/REF-003 decisions
block the Bybit-dependent path.

## Useful observations that are NOT authority
Launch/scheduled-delivery metadata (e.g. Bybit launchTime; BTCUSDU26 scheduled future
`deliveryTime`, which is not an observed completed delivery) and bounded earliest/latest
timestamps within sampled/archive objects remain useful observations but do not constitute
implementation authority (G02/G03 PASS_PARTIAL, blocking). Bounded sample/archive edges are
not proven asset-lifetime first/last trades and must never be equated with exact
listing/delisting lifecycle events.

## Accepted decisions that block Bybit
- REF-002 accepted NO AUTHORITY (REVIEW-0102): blocks Bybit historical instrument event
  authority.
- REF-003 accepted NO_AUTHORITY (REVIEW-0118): blocks Bybit prospective snapshot authority.
No accepted cross-venue source closes the remaining gaps.

## Unproven / failing gates
- G04: announcement known-time and effective-time history unproven.
- G05: historical state-transition and revision/vintage history unproven.
- G06: representative delisted/failed-asset coverage, final tradable price, and failure
  cause not demonstrated.
- G07: required source licensing and internal raw-retention authority not established.
- G08: DF-08 required known-delisting reconstruction test not passed.

## Decision
`NO_SURVIVORSHIP_FREE_UNIVERSE_AUTHORITY`. Blocking gates: G02, G03, G04, G05, G06, G07,
G08 (G01 non-blocking PASS). Historical universe construction and all dependent factor work
remain blocked. No collector, schema, universe implementation, or next ticket authorized.
