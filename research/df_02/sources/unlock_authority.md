# Source authority note — Point-in-time token unlock (DF-02 synthesis)

Synthesis target: whether accepted repository evidence authorizes point-in-time token-unlock
schedules (historical unlock-schedule vintages, announcement/revision known-time, and actual
on-chain unlock execution). Evidence synthesis only; no new factual inference.

## What is repository-native (used here)
Only accepted inventory, hashes, decisions, and prior accepted review findings are used.
The fourteen artifacts registered in `EVIDENCE_REGISTER.csv` span: sprint_002/06
(DF-02 question + reconstruction test), sprint_003/01..05, /07, /08, /09, /13
(source decision register, object inventory, schema/semantics audit, PIT reference plan,
revision audit, vendor trial requirements, research data decisions, open questions, research
lead decisions), sprint_003/sources (token_unlocks.md, defillama.md), and audit_results
(evidence_reconciliation.csv, hash_verification.json).

## Preserved accepted roles (must not be altered)
- Tokenomist — DEFERRED for the audited environment.
- Messari — CONDITIONAL / EXPLORATORY_PHASE2.
- DefiLlama unlock adapters — CONDITIONAL / REFERENCE_METADATA.

## Access facts (not universal unreachability)
Tokenomist was TLS-unreachable in the audited environment; Messari required account/key
access; DefiLlama emissions returned HTTP 402. These are audited-environment access failures
only. G01 FAIL_ACCESS (blocking) — do not claim universal unreachability.

## No historical vintages
Current schedules or adapter code cannot be treated as historical vintages. Vintage
preservation (G02), announcement/revision known-time (G03), actual on-chain execution (G04),
token/contract/chain mapping (G05), licensing/retention (G07), and the known-unlock
reconciliation test (G08) are all unproven. Coverage (G06) is partial: some adapter artifacts
exist but representative token/asset output coverage is not demonstrated.

## Downstream
- DIL-01 remains DEFERRED/UNTESTED.
- DF-01's accepted supply blocker remains independent and unchanged.
- No unlock collector, factor, schema, implementation, procurement, or next ticket authorized.

## Decision
`NO_POINT_IN_TIME_UNLOCK_AUTHORITY`. All eight gates are blocking (G01 FAIL_ACCESS;
G02/G03/G04/G05/G07/G08 FAIL_UNKNOWN; G06 FAIL_PARTIAL). Point-in-time unlock schedules
cannot be authorized from retained evidence.
