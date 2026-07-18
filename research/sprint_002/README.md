# Research Sprint 002 — 2025–2026 Literature Refresh

**Status:** Literature and research-design refresh (no empirical results)
**Created:** 2026-07-18
**Research cutoff:** 2026-07-18
**Depends on:** Sprint 001 (frozen), `research/evidence/hypotheses.yaml` v1

## What this sprint is

Sprint 002 is a **literature and research-design refresh**. It contains no empirical
results from our platform and does **not** claim that any factor is validated. It:

- refreshes the evidence base with peer-reviewed and working papers from 2025–2026;
- records explicit research-design decisions for the existing factor families;
- adds the `DIL-01` token-dilution candidate and a new `H-011` hypothesis;
- documents the data-feasibility backlog that gates empirical testing of new families;
- preserves Sprint 001 as a frozen historical record (no edits, no re-hashing).

Every bibliographic claim in this sprint was independently verified against its primary
publisher / repository page on or before the research cutoff.

## Layout

```text
research/sprint_002/
├── README.md
├── 00_SCOPE_AND_SEARCH_METHOD.md
├── 01_LITERATURE_REFRESH_2025_2026.md
├── 02_LITERATURE_LEDGER.csv
├── 03_SPRINT_001_ERRATA.csv
├── 04_RESEARCH_DECISIONS.csv
├── 05_FACTOR_ROADMAP_UPDATE.md
├── 06_DATA_FEASIBILITY_BACKLOG.csv
├── 07_OPEN_RESEARCH_QUESTIONS.md
├── CHANGELOG.md
└── factor_cards/
    ├── DIL-01_token_dilution.md
    ├── MOM-01_literature_addendum.md
    ├── LIQ-01_literature_addendum.md
    ├── CARRY-01_literature_addendum.md
    └── NET-01_literature_addendum.md
```

## Source ID convention

Sprint 002 continues the Sprint 001 ledger. New sources are `LIT-024` … `LIT-037`.
Sprint 001 sources `LIT-001` … `LIT-023` are not duplicated here; they are cited by
reference where relevant.

## Relationship to the control plane

This is a research-document task. It does not change the active engineering ticket
(`GOV-001`), does not authorize `RAW-001` or any implementation ticket, does not mark any
hypothesis `SUPPORTED`, and does not modify production code or the frozen Sprint 001
records.
