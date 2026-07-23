# EXP-001 — Change Report (Jr Integration after REVIEW-0147)

**Source approved under:** REVIEW-0147 — EXP-001 SOURCE APPROVED / JR INTEGRATION AUTHORIZED
(authorized REVIEW-0146)
**Base commit:** c8c2f45
**Jr work commit:** see git log (EXP-001: JR integration after REVIEW-0147)

## Scope
Jr-side integration only. The Sr production source drop is unchanged; Jr added package exports,
focused tests, the change report, and governance records.

## Approved source drop (kept exactly as dropped — NOT modified)
- `src/cryptofactors/validation/experiment.py` (167 lines) — `ExperimentBundle` (frozen/slots,
  deterministic SHA-256 fingerprint via canonical serialization), `ExperimentRegistry`
  (Protocol), `InMemoryExperimentRegistry` (`register` recomputes the fingerprint and rejects
  tampered/duplicate bundles; `load`/`list_bundles`/`has` with fail-closed semantics).

## Jr-added surface (not Sr logic)
- `src/cryptofactors/validation/__init__.py`: exported `ExperimentBundle`, `ExperimentError`,
  `ExperimentRegistry`, `InMemoryExperimentRegistry`.
- `tests/validation/test_exp001_integration.py` — 16 focused tests.
- `docs/reviews/EXP-001_CHANGE_REPORT.md` — this report.

## Exact gate results
- **pytest** `tests/validation/ -q --tb=line`: **53 passed** (16 LABEL-001 + 21 SPLIT-001 +
  16 EXP-001).
- **ruff** `src/cryptofactors/validation tests/validation`: `All checks passed!`
- **mypy** `--no-error-summary src/cryptofactors/validation tests/validation`: no `no-untyped-def`
  / type errors in the new test file. Remaining diagnostics are inside the Sr-approved drops:
  - `src/cryptofactors/validation/split.py:280` — unused `type: ignore` (pre-existing).
  - `src/cryptofactors/validation/labels.py:225` — unused `type: ignore` (pre-existing).
  - `src/cryptofactors/validation/experiment.py:70` — `Mapping[object, object]` assignment
    incompatibility in the Sr drop; left unchanged per Jr scope (Sr-source defect, not Jr-introduced).
- **repo control** `python3 scripts/check_repo_control.py`: **PASS**.

## Test coverage summary
- Construction validation: non-string factor IDs (`int`) -> `ExperimentError`; empty factor_defs
  -> `ExperimentError`; non-string metadata keys (`int`) -> `ExperimentError`; non-scalar metadata
  values (`None`) -> `ExperimentError`.
- Determinism: identical inputs yield identical 64-char SHA-256 fingerprints; factor_defs are
  sorted canonically.
- Fingerprint tampering: after construction, mutating `factor_defs` or `metadata` (bypassing the
  frozen dataclass) and calling `register` raises `ExperimentError` ("fingerprint does not match")
  — the registry recomputes and rejects.
- Happy paths: `register` returns the fingerprint and records the bundle; duplicate `register`
  raises "duplicate"; `load` round-trips factor_defs/metadata; `load` of an unknown fingerprint
  raises "not found"; `has` returns True/False correctly; `register` of a non-bundle raises.
- Distinct bundles yield distinct fingerprints and both list.

## States
All EXP-001 states already `AWAITING_REVIEW` (Reviewer next, Next ticket NONE) in
`tickets/EXP-001.md`, `IMPLEMENTATION_BACKLOG.csv`, `README.md`, `CURRENT_TASK.md`. REVIEW-0147
referenced.

## Note
No new production features beyond the approved EXP-001 contract. No Sr-source edits. The only
mypy item inside `src/cryptofactors/validation` beyond the pre-existing unused-ignores is a
type-assignment nit at `experiment.py:70` in the approved Sr drop, left unchanged per the
Jr-integration boundary. Stop after push.
