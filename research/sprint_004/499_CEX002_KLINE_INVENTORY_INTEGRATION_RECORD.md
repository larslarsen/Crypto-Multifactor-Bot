# CEX-002 Record 499 — Kline inventory integration

Ticket: CEX-002, IN_PROGRESS; next ticket NONE
Actor: Jr Dev — Hermes
Model: meituan/longcat-2.5-preview:free (Nous Portal), no reasoning override
Reviewer: Lead Quantitative Finance Researcher/Engineer
Governing: Review 498 `research/sprint_004/498_CEX002_RETAINED_KLINE_INVENTORY_CORRECTION.md`, ADR-0037

## Outcome

Review 498's three-path retained-inventory correction was validated and integrated. The fix
authenticates the finite retained inventory separately, enforces production kind counts and
filename hashes, and leaves the descriptor closure required; it affects prepared authority
metadata only. The developer's separate 35-case result is distinguished below from Hermes's
own validation.

## Final source/test identities

| path | SHA-256 | lines | status |
| --- | --- | --- | --- |
| src/cryptofactors/ingest/binance_usdm_harmonic_bundle.py | 6018280a0ed9ab16b585875e7f1c3bd3bc96233c90407b1b5bcb7f2a222c276a | 1921 | changed |
| scripts/research/publish_binance_usdm_harmonic_bundle.py | cfb5b04f87226c9d1efbb39bbd04b634c40c7a20ddb868b8c6b3768d817b3fd9 | 102 | changed |
| tests/ingest/test_binance_usdm_harmonic_bundle.py | 08fc013675d70d31c3ef578d7c2ce810979485ecded032a916f0a29832ee02b9 | 1203 | changed |
| src/cryptofactors/catalog/dataset/cex002_reference_release.py | 942140dbbc85a4b7cb7f24284442edf8b8289705651895be7cdaa076ddaa8387 | 2139 | unchanged (Record 495) |
| tests/catalog/test_cex002_reference_release.py | e4d7cf4335e87d8e7bb4ecb2f87dd106f601e845c47e369f095a784fe3c5f456 | 1020 | unchanged (Record 495) |

## Developer result (not Hermes's validation)

The selected GPT-6 Sol High developer completed the bounded correction and stopped. Its
single authorized targeted pytest returned exit 0 with 35 passing cases. The reviewer
inspected the production and test diffs and independently verified the final bytes.

## Hermes validation (exact commands and results)

Pre-checks: HEAD == origin/main == `9402536f8d05981da1e2c48fca0710719fdf0a0e`; index empty
(0 staged); all five source/test hashes matched the accepted bytes; the bundle root
`data/.cex002_harmonic_bundle` was absent (`test -e` exit 1) and not a dangling symlink
(`test -L` exit 1).

```
.venv/bin/python -m pytest -q tests/catalog tests/ingest/test_binance_usdm_harmonic_bundle.py
  -> exit 0; 134 passed (67 + 67; progress [53%]/[100%])
```

```
.venv/bin/ruff check src/cryptofactors/ingest/binance_usdm_harmonic_bundle.py scripts/research/publish_binance_usdm_harmonic_bundle.py tests/ingest/test_binance_usdm_harmonic_bundle.py
  -> exit 0; All checks passed!
```

```
.venv/bin/python scripts/check_repo_control.py
  -> exit 0; Repo control check: PASS
```

## Integration

- Staged exactly four paths: the three changed source/test paths above plus this Record 499.
- `git diff --cached --check`: exit 0, no output.
- Staged path list and committed blob identities verified.
- Commit and normal push executed; HEAD equals origin/main and the index is empty.
- The full source integration commit is `SOURCE_COMMIT` (literal value recorded in this
  record's commit step). The five committed blobs at that commit match the frozen hashes above.
- No `git add -A`, no unrelated staging, no amend/reset/force push.

## Scope limits and gaps

- No real prepare, publish, consumer or data operation occurred in this integration.
- Final release acceptance remains pending; this record claims integration only.
- The two unchanged catalog paths were not modified.
- Unrelated working-tree changes and reviewer governance edits were preserved.

## Record status

Record 499 is implementation evidence owned by Hermes. CEX-002 remains IN_PROGRESS;
next ticket NONE; reviewer acceptance remains exclusive.
