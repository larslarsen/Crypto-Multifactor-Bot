# ASOF-001 — Change Report (Jr Integration after REVIEW-0138)

**Source approved under:** REVIEW-0138 — ASOF-001 SOURCE APPROVED / JR INTEGRATION AUTHORIZED
**Base commit:** 0099bbf (DF-07 acceptance; ASOF-001 source drop already present uncommitted)
**Jr work commit:** see git log (ASOF-001: JR integration after REVIEW-0138 source approval)

## Scope
Jr-side integration only. The Sr production source drop is unchanged; only tests, change
report, and governance records were added.

## Approved source drop (kept exactly as dropped — NOT modified)
- `src/cryptofactors/catalog/as_of.py` (769 lines) — `AsOfStore` protocol + `CatalogAsOfStore`
  with `latest_available` / `as_of` and strict bitemporal eligibility.
- `src/cryptofactors/catalog/__init__.py` — public exports of the as-of contract.

## New files (Jr)
- `tests/catalog/test_asof001_integration.py` — 22 focused tests.
- `docs/reviews/ASOF-001_CHANGE_REPORT.md` — this report.

## Test files
`tests/catalog/test_asof001_integration.py` (single new test module).

## Exact gate results
- **pytest** `tests/catalog/test_asof001_integration.py -q --tb=line`:
  `22 passed`.
- **ruff** `src/cryptofactors/catalog tests/catalog`: `All checks passed!`
- **mypy** `--no-error-summary src/cryptofactors/catalog tests/catalog`:
  no `no-untyped-def` / type errors in the new test file. Remaining `import-untyped`
  diagnostics are pre-existing repo-wide (the `cryptofactors` package ships without a
  `py.typed` marker) and apply equally to `src/cryptofactors/catalog`; out of scope for
  this Jr ticket.
- **repo control** `python3 scripts/check_repo_control.py`: `PASS`.

## Test coverage summary
- `observation_eligible` / `reference_eligible` rules (availability required; future
  availability rejected; half-open valid window; known-after-knowledge rejected).
- `CatalogAsOfStore.latest_available` / `as_of` on all three dataset kinds:
  - `market_bars` (BAR-001): picks newest period per key; respects decision time;
    `as_of` returns all eligible; missing key → empty; `max_age` filters old availability.
  - `ref_fee_schedule` (FEE-001): latest window after decision time; empty before first
    window; empty when knowledge time after `known_to`.
  - `ref_instrument_version` (REF-001): latest higher `version_seq`; `as_of` returns the
    single eligible version at decision time.
- Error cases: unsupported dataset; missing `dataset_store_root`; naive (non-UTC) decision
  time; negative `max_age`; requested field not present; empty key list → empty.
- Factor-path smoke: the `AsOfStore` contract is importable from `cryptofactors.catalog`
  so factor code consumes it instead of reimplementing temporal joins.

## States
After this commit all ASOF-001 states set to `AWAITING_REVIEW` (Reviewer next, Next ticket
NONE): `tickets/ASOF-001.md`, `IMPLEMENTATION_BACKLOG.csv`, `README.md`, `CURRENT_TASK.md`.
REVIEW-0138 referenced in governing docs.

## Note
No new production features beyond the approved `AsOfStore` contract. No Sr-source edits.
Stop after push.
