# REVIEW-0135 — DF-07 ON-CHAIN OBSERVATION AUDIT AUTHORIZED

**Authorized ticket:** DF-07
**Auditor:** Jr Dev — Hermes
**Date:** 2026-07-22
**Decision:** AUTHORIZE — create and complete DF-07.

## Authorization

DF-07 ("Point-in-Time On-Chain Observation Authority Audit") is authorized as an
evidence-synthesis-only task. Determine whether accepted repository evidence authorizes
point-in-time on-chain observations (blocks, addresses, fees, and the required known-block
publication/revision audit test). Required decision:
`POINT_IN_TIME_ON_CHAIN_OBSERVATION_AUTHORITY` or
`NO_POINT_IN_TIME_ON_CHAIN_OBSERVATION_AUTHORITY`.

- Priority: P1
- Gate role: BLOCKING_FOR_NET_DILUTION_ON_CHAIN
- Status: IN_PROGRESS

## Scope

Repository-native evidence synthesis only. No network access, procurement, production code,
tests, schema, collectors, factors, or new factual inference.

## Preserved boundaries (exact)
- SRC-006 observations/catalog are accepted REFERENCE_METADATA, but NET-01 use remains conditional.
- Coin Metrics Community remains CONDITIONAL - EXPLORATORY_PHASE2.
- SRC-006b remains CONDITIONAL because publication-time and revision behavior are unbounded.
- SRC-010 remains CONDITIONAL and was not queried.
- RD-05 is a conditional finding and next action, not authority.
- RD-07 does not override source-specific conditions or authorize on-chain data.
- DF-01 remains accepted with NO_PRIMARY_PIT_SUPPLY_AUTHORITY and does not itself resolve DF-07.

## Eight blocking gates
- G01 — source role and authority for blocks, addresses, and fees
- G02 — metric semantics, chain mappings, and entity/spam treatment
- G03 — block/event time versus indexer publication/known time
- G04 — revisions, backfills, and historical-vintage preservation
- G05 — chain/asset/metric coverage and archival depth
- G06 — raw provenance, request identity, hashes, versions, and retrieval time
- G07 — licensing and internal acquisition/retention authority
- G08 — reproduce the required known-block publication/revision audit test

## Authority rule
Authority requires all eight gates to PASS. Return DF-07 to AWAITING_REVIEW; Reviewer next;
Next ticket authorized NONE. Do not authorize NET-01, DIL-01, collection, procurement,
implementation, schema, tests, or another ticket.
