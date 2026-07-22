# SPLIT-001 — Change Report (Jr Integration after REVIEW-0141)

**Source approved under:** REVIEW-0141 — SPLIT-001 SOURCE APPROVED / JR INTEGRATION AUTHORIZED
(authorized REVIEW-0140)
**Base commit:** 875ea8b
**Jr work commit:** see git log (SPLIT-001: JR integration after REVIEW-0141)

## Scope
Jr-side integration only. The Sr production source drop is unchanged; only tests, change
report, and governance records were added.

## Approved source drop (kept exactly as dropped — NOT modified)
- `src/cryptofactors/validation/split.py` (487 lines) — `ChronologicalSplitter` protocol +
  `PurgedChronologicalSplitter` with `WALK_FORWARD` / `EXPANDING` / `PURGED_KFOLD` modes,
  `purge_train_events`, `EventInterval` / `SplitConfig` / `OuterFold`, injected
  `AsOfDataAccess` (structural, no catalog import).
- `src/cryptofactors/validation/__init__.py` — public exports of the split contract.

## New files (Jr)
- `tests/validation/test_split001_integration.py` — 21 focused tests.
- `docs/reviews/SPLIT-001_CHANGE_REPORT.md` — this report.

## Test files
`tests/validation/test_split001_integration.py` (single new test module).

## Exact gate results
- **pytest** `tests/validation/ -q --tb=line`: **21 passed**.
- **ruff** `src/cryptofactors/validation tests/validation`: `All checks passed!`
- **mypy** `--no-error-summary src/cryptofactors/validation tests/validation`: no
  `no-untyped-def` / type errors in the new test file. Remaining `import-untyped` diagnostics
  are pre-existing repo-wide (`cryptofactors` package ships without a `py.typed` marker) and
  apply equally to `src/cryptofactors/validation`; out of scope for this Jr ticket.
- **repo control** `python3 scripts/check_repo_control.py`: **PASS**.

## Test coverage summary
- Event-interval contract: rejects naive (non-UTC) timestamps, `event_end <= event_start`,
  and `decision_time > event_end`.
- Config validation: PURGED_KFOLD requires n_folds>=2; WALK_FORWARD/EXPANDING require positive
  spans; negative embargo rejected; min events >=1.
- `purge_train_events` unit behavior: purges events whose `event_end` passes the test purge
  horizon; retains non-leaking events; respects embargo gap.
- All three modes produce ordered `OuterFold`s: walk-forward, expanding (train window starts at
  global t0), purged K-fold (first block skipped fail-closed when it has no prior train).
- Purge + embargo enforced inside produced folds: no train/test event overlap; embargo gap
  present; purged-K-fold test blocks are disjoint by event.
- AsOf injection + instrument eligibility: splitter rejects `None` store; missing instrument at
  a decision time fails closed (`instrument not eligible`); real `CatalogAsOfStore` injected
  end-to-end resolves REF-001 instruments and produces folds (proves the AsOfDataAccess surface
  matches without the validation module importing catalog).
- Error paths: empty events, insufficient history (train_span > available), purged-K-fold with
  too few distinct decision times — all fail closed with `SplitError`.

## States
After this commit all SPLIT-001 states set to `AWAITING_REVIEW` (Reviewer next, Next ticket
NONE): `tickets/SPLIT-001.md`, `IMPLEMENTATION_BACKLOG.csv`, `README.md`, `CURRENT_TASK.md`.
REVIEW-0141 referenced in governing docs.

## Note
No new production features beyond the approved `ChronologicalSplitter` contract. No Sr-source
edits. Stop after push.
