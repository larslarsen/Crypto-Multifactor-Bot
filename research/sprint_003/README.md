# Research Sprint 003 — Data-Source Feasibility Audit

**Status:** append-only research/data-source audit (no empirical factor results)
**Created:** 2026-07-18
**Research cutoff:** 2026-07-18
**Depends on:** Sprint 001 (frozen), Sprint 002 (frozen), `research/evidence/hypotheses.yaml` v1

## What this sprint is

Sprint 003 audits the **feasibility of the data sources** required before any Sprint 002
factor (especially `DIL-01`, `NET-01`, and the realistic-momentum diagnostics from `LIT-038`)
can be empirically tested. It is a data-source audit, not a factor backtest. It:

- acquires bounded public samples from official English-language endpoints;
- records provider, role, endpoint, parameters, retrieval time, HTTP status, SHA-256,
  sizes, row counts, time ranges, field schemas, and revision/replacement behavior;
- assigns each source a decision (`ACCEPT` / `CONDITIONAL` / `DEFER` / `REJECT`) and an
  architecture role;
- documents point-in-time reconstruction evidence for listing/delisting events;
- flags access, license, and point-in-time gaps honestly.

No large market-data objects are committed. Only bounded registries, audit CSVs, source
notes, and small fixtures (stored outside the repo at `/tmp/s3audit/fixtures`) are kept;
hashes and audit results for everything else are recorded here.

## Layout

```text
research/sprint_003/
├── README.md
├── 00_AUDIT_SCOPE_AND_METHOD.md
├── 01_SOURCE_DECISION_REGISTER.csv
├── 02_SOURCE_OBJECT_INVENTORY.csv
├── 03_SCHEMA_AND_SEMANTICS_AUDIT.csv
├── 04_POINT_IN_TIME_REFERENCE_PLAN.md
├── 05_CORRECTION_AND_REVISION_AUDIT.md
├── 06_STORAGE_AND_COVERAGE_ESTIMATES.csv
├── 07_VENDOR_TRIAL_REQUIREMENTS.md
├── 08_RESEARCH_DATA_DECISIONS.csv
├── 09_OPEN_QUESTIONS.md
├── CHANGELOG.md
└── sources/
    ├── binance.md  kraken.md  okx.md  bybit.md
    ├── coin_metrics.md  defillama.md  token_unlocks.md
```

## Relationship to the control plane

Documentation/research only. No engineering ticket authorized, no ingestion production
code written, no commercial dataset purchased, no secrets committed. The active ticket
(`GOV-001`) and `research/evidence/hypotheses.yaml` (including `H-011` `DIL-01`,
`H-007` `NET-01`) are unchanged. `DIL-01` and `NET-01` are explicitly **not** marked
research-ready by this audit; their gating data requirements remain open.
