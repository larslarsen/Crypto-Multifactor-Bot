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

## Source-specific roles (preserved from E02 — 01_SOURCE_DECISION_REGISTER.csv)
- Tokenomist — DEFERRED.
- Messari — CONDITIONAL / EXPLORATORY_PHASE2.
- DefiLlama unlock adapters — CONDITIONAL / REFERENCE_METADATA.

## Research Lead decisions (E10 — 13_RESEARCH_LEAD_DECISIONS.md, verbatim)
- DefiLlama = CONDITIONAL - EXPLORATORY_PHASE2; emissions access not established as free.
- Tokenomist / Messari = DEFER pending authorized access or vendor trial.
- DIL-01 remains deferred.
E10 is the Research Lead decision record; the separate source-register roles above are from E02.

## Access facts (not universal unreachability)
- E03 (object inventory) records: Tokenomist TLS error (TLSV1_UNRECOGNIZED_NAME), Messari
  404/429 no-key gap, and the old DefiLlama SDK path returning 404 (INVALID_NONQUALIFYING).
  E03 does NOT record the DefiLlama emissions HTTP 402 (that is E12) and does NOT establish
  retained adapter artifacts.
- E11 (token_unlocks source note) details Tokenomist/Messari; E12 (defillama source note)
  records the DefiLlama emissions HTTP 402 (paid); E07 records trial prerequisites.
G01 FAIL_ACCESS (blocking) — audited-environment access failures only; do not claim universal
unreachability.

## No historical vintages
E04 (schema/semantics audit) records Tokenomist's expected schema as unconfirmed, vintage
preservation as unknown (CANNOT CONFIRM vintage preservation), and on-chain vesting as required
but unqueried. No observed on-chain execution fields are described. Current schedules or
adapter code cannot be treated as historical vintages. Vintage preservation (G02),
announcement/revision known-time (G03), actual on-chain execution (G04), token/contract/chain
mapping (G05), licensing/retention (G07), and the known-unlock reconciliation test (G08) are
all unproven. Coverage (G06) is partial: E13 proves retained adapter-file artifacts
(paths/sizes/hashes), E12 provides DefiLlama adapter/access context, and E11 describes a
partial bridge, but representative token/asset output coverage is not demonstrated. G07: E07
records vendor/licensing prerequisites; E11 warns that unlock aggregators may have
commercial/licensed terms requiring confirmation before retention or redistribution — not all
unlock data is proven commercially licensed.

## Downstream
- DIL-01 remains DEFERRED/UNTESTED.
- DF-01's accepted supply blocker remains independent and unchanged.
- No unlock collector, factor, schema, implementation, procurement, or next ticket authorized.

## Decision
`NO_POINT_IN_TIME_UNLOCK_AUTHORITY`. All eight gates are blocking (G01 FAIL_ACCESS;
G02/G03/G04/G05/G07/G08 FAIL_UNKNOWN; G06 FAIL_PARTIAL). Point-in-time unlock schedules
cannot be authorized from retained evidence.
