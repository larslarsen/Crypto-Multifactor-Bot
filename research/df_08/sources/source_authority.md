# Source authority note — Survivorship-free universe (DF-08 synthesis)

Synthesis target: whether accepted repository evidence authorizes construction of a
survivorship-free historical universe (complete listing/delisting events, final tradable
price, and failure cause per asset). Evidence synthesis only; no new factual inference.

## What is repository-native (used here)
Only accepted inventory, hashes, decisions, and prior accepted review findings are used.
The fourteen artifacts registered in `EVIDENCE_REGISTER.csv` span: sprint_002/06
(DF-08 question + reconstruction test), sprint_003/01, /02, /04, /08 (source decisions,
object inventory, PIT reference plan, research data decisions), REF-001 acceptance
(REVIEW-0017), and the accepted REF-002 and REF-003 chains (tickets, reports, acceptance
reviews, decision matrices).

## Accepted substrate (must not be downgraded)
- REF-001 provides an accepted bitemporal identity/event-storage substrate only (G01 PASS).
- Accepted market-bar authority is preserved.
These are storage/identity substrates, not survivorship-free event authority.

## Useful observations that are NOT authority
Sprint-003 listing/launch/delivery exemplars and first/last trade edges remain useful
observations but do not constitute implementation authority (G02/G03 PASS_PARTIAL,
blocking). Trade edges must not be equated with exact listing/delisting events.

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
