# CEX-002 Known-Release Reconciliation Integration Record

## Integration result

All integration checks passed in order; first-failure stop was not triggered.

| Step | Check | Exit status | Notes |
|------|-------|-------------|-------|
| 1 | Scoped Ruff on new script + test | `0` | `All checks passed!` |
| 2 | Repo control script | `0` | `Repo control check: PASS` |
| 3 | `git diff --check` | `0` | No whitespace errors |

## Source/test provenance and attribution

- Reconciliation source: `scripts/research/reconcile_cex002_admitted_release.py`
  - Frozen SHA-256: `857aec234bc5ebb5905a32d6383fb7f7d59cbf8dbf6da435c5042fd1b095041b`
  - Attribution: senior-authored source accepted after 25 focused cases passed (exit 0, 3.77s) in Review 522.

- Reconciliation test: `tests/test_cex002_admitted_release_reconciliation.py`
  - Frozen SHA-256: `e0f3d7e8d5b5e66a2daa431f4fd3d7b6c4b886d1c8cbb4fb18d01df8f92ec768`
  - Attribution: same senior test evidence as source; no new test design or retry.

## First-failure history

The earlier focused validation run recorded `21 passed, 2 failed` before the
accepted 25-pass result. That non-zero result is preserved as evidence; the
final accepted state is the 25-pass/exit-0 outcome. No retry was performed
after the accepted state.

## Environment and model notes

- Model at integration: `stepfun/step-3.7-flash:free` via Nous Portal live free list.
- Prior session (`20261020_164842_bdb19d`) used Laguna; that endpoint was retired
  (HTTP 404) and capacity recovery was confirmed before this record was written.
- No source or test edits were made. No extra agents were used.

## Git state at integration

- HEAD: `b99a747112de3654bcee3a9280a05f39a0c205ff`
- origin/main: `b99a747112de3654bcee3a9280a05f39a0c205ff`
- Staged paths (guard): `scripts/research/reconcile_cex002_admitted_release.py`, `tests/test_cex002_admitted_release_reconciliation.py`, `research/sprint_004/523_CEX002_KNOWN_RELEASE_RECONCILIATION_INTEGRATION_RECORD.md`
- Unrelated dirty paths: preserved untouched (`opencode.json`, `src/cryptofactors/acquisition/uniswap_v2_pair_events_v2_engine.py`, `tests/acquisition/test_uniswap_v2_pair_events_v2_engine.py`).
