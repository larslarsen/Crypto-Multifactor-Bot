# Source note — Coin Metrics Community (DF-01 synthesis)

Synthesis target: whether accepted Sprint-003 Coin Metrics Community evidence authorizes
historical point-in-time circulating / max / FDV supply. Evidence synthesis only.

## What is repository-native (used here)
Only the accepted inventory, hashes, and audit findings for Coin Metrics Community are
retained in the repository. The ten artifacts registered in `EVIDENCE_REGISTER.csv` are:
sprint_002/06_DATA_FEASIBILITY_BACKLOG.csv, sprint_003/01_SOURCE_DECISION_REGISTER.csv,
sprint_003/02_SOURCE_OBJECT_INVENTORY.csv, sprint_003/03_SCHEMA_AND_SEMANTICS_AUDIT.csv,
sprint_003/05_CORRECTION_AND_REVISION_AUDIT.md, sprint_003/08_RESEARCH_DATA_DECISIONS.csv,
sprint_003/13_RESEARCH_LEAD_DECISIONS.md, sprint_003/audit_results/evidence_reconciliation.csv,
sprint_003/audit_results/hash_verification.json, sprint_003/sources/coin_metrics.md.

## What is NOT repository-retained
The original Coin Metrics Community API response bodies are **not** retained in the
repository. Only their accepted inventory rows, request identities, SHA-256 hashes, and
audit conclusions remain. Do not claim the original API bodies are repository-native.

## Accepted role (must not be overruled)
Across Sprint-003, Coin Metrics Community is accepted only as conditional
`REFERENCE_METADATA` / `EXPLORATORY_PHASE2`. It is not a primary point-in-time supply
authority. This synthesis preserves that accepted status and adds no new factual inference.

## Semantic notes (from accepted audits)
- `SplyCur` is an issued/current supply field, not circulating float.
- Future unissued / max supply series are absent from the retained inventory.
- Server-side revisions/backfills exist; no historical vintages retained.
- Licensing and internal raw-retention authority were not established.

## Decision
`NO_PRIMARY_PIT_SUPPLY_AUTHORITY`. Blocked gates: G01, G02, G03, G04, G05, G06, G07, G08.
SIZE-01, DIL-01, and supply-dependent NET-01 work remain blocked. No prospective collector
or implementation authority is granted.
