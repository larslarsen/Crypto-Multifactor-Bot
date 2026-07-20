# RES-001 — Change Report

**Ticket:** RES-001 - Post-Sprint-003 Research Protocol Reconciliation
**Date:** 2026-07-20
**Accepted foundation:** BAR-001 integration commit `c10dd3a` (REVIEW-0042)

## Scope

Documentation-only integration of the reviewer-authored Sprint 004 drop. No
production source, tests, architecture, ADRs, or implementation-roadmap changes.

## Integrated records

- `research/sprint_004/` — Sprint 004 protocol reconciliation (reviewer-authored):
  - README.md, 00_EXTERNAL_REVIEW_TRIAGE.md, 01_MOMENTUM_OPERATIONALIZATION.md,
    02_VALIDATION_CAPACITY_AND_REGIMES.md, 03_DEFERRED_FACTOR_DATA_GATES.md
  - 04_RESEARCH_DECISIONS.csv (RD-09..RD-16), 05_EXPERIMENT_REGISTRATIONS.csv
    (EXP-2026-019, EXP-2026-020)
  - factor_cards/MOM-TS-01_time_series_momentum.md
- `research/evidence/hypotheses.yaml` — registry_version 1→2; appended H-012
  (time-series momentum, REGISTERED/UNTESTED). H-001..H-011 unchanged (append-only).
- `research/evidence/README.md` — wording updated to "append-only" registry.
- `tickets/RES-001.md`, `README.md`, `docs/handoff/CURRENT_TASK.md` — ticket wiring.

## Inspection results

- **Internal links:** Sprint 004 layout tree matches the actual file set; the
  referenced `factor_cards/MOM-TS-01_time_series_momentum.md` exists. No markdown
  cross-links to missing files.
- **CSV/JSON syntax:** `04/05_*.csv` parse cleanly (consistent column counts).
  `hypotheses.yaml` passes `python3 -m json.tool` (acceptance command 1).
- **Append-only history:** H-012 appended; prior hypotheses unmodified. Registry
  `as_of` advanced 2026-07-18 -> 2026-07-20. No in-place edits of frozen Sprint
  001-003 records.
- **No accidental architecture/source changes:** `git diff -- src/` and
  `docs/handoff/IMPLEMENTATION_SEQUENCE.md` are empty. Scientific decisions (MOM-TS-01
  separate from MOM-01, deferred joint mom/carry, DIL-01/NET-01 gates, holdout rule)
  left intact.
- **Cross-consistency:** RD-09 references H-012 (registered); EXP-2026-019/020
  reference MOM-TS-01; all status = BLOCKED_DATA / untested (no empirical claims).

## Acceptance commands (exact)

1. `python3 -m json.tool research/evidence/hypotheses.yaml >/dev/null` — OK
2. `PYTHONPATH=src uv run pytest -q --tb=short` — 367 passed (1 pre-existing archive warning)
3. `python3 scripts/check_repo_control.py` — PASS

## Stop condition

Records committed and pushed; stopped for reviewer inspection. Next ticket
authorized: NONE.
