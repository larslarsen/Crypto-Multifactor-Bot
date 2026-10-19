# CEX-002 Record 505 — Liquidation gap accounting integration

Ticket: CEX-002, IN_PROGRESS; next ticket NONE
Actor: Jr Dev — Hermes
Model: meituan/longcat-2.5-preview:free (Nous Portal), no reasoning override
Reviewer: Lead Quantitative Finance Researcher/Engineer
Governing: Review 504 `research/sprint_004/504_CEX002_LIQUIDATION_GAP_ACCOUNTING_CORRECTION.md`, ADR-0037

## Outcome

Review 504's two-path liquidation category/comparison correction was validated and
integrated. The category checks retain every accepted gap table/lineage, keep separate
quality and authority accounting, preserve the physical total, and enforce the existing
quality pin plus the explicit 202 authority pin. The comparison is authenticated before a
bounded 1 MiB read, retains the accepted `pending_reviewer` history marker, and enters the
manifest once as zero-row metadata. The production entry pin remains 18; no comparison is
rerun and no OI equality is claimed. The developer's initial test assertion failure and
passing continuation are distinguished below from Hermes's own validation.

## Final source/test identities

| path | SHA-256 | lines | status |
| --- | --- | --- | --- |
| src/cryptofactors/ingest/binance_usdm_harmonic_bundle.py | 1c9214d088c4279cf34e78c24d97a9bc14124491c27f5575edcca67c675cb48b | 1996 | changed |
| tests/ingest/test_binance_usdm_harmonic_bundle.py | 867125b2c123349abe56caa1f8c5e8ec5cc8342dc1909cb4029d123af364f2e0 | 1383 | changed |
| scripts/research/publish_binance_usdm_harmonic_bundle.py | cfb5b04f87226c9d1efbb39bbd04b634c40c7a20ddb868b8c6b3768d817b3fd9 | 102 | unchanged (Review 498) |
| src/cryptofactors/catalog/dataset/cex002_reference_release.py | 942140dbbc85a4b7cb7f24284442edf8b8289705651895be7cdaa076ddaa8387 | 2139 | unchanged (Review 495) |
| tests/catalog/test_cex002_reference_release.py | e4d7cf4335e87d8e7bb4ecb2f87dd106f601e845c47e369f095a784fe3c5f456 | 1020 | unchanged (Review 495) |

## Developer history (not Hermes's validation)

The same GPT-6 Sol High actor fixed the liquidation category mixing (4,626 daily vs 202
authority) plus the omitted accepted comparison JSON. Its first targeted run returned
49 passed / 1 failed (a manifest assertion); the fixture-only assertion correction then
produced a passing run of all 50 cases, exit 0, with no production-byte change after the
first result. The reviewer inspected all final changes and independently verified the hashes.

## Hermes validation (exact commands and results)

Pre-checks: HEAD == origin/main == `289910a087f743123bbf0168a8e50c6008930c54`; index empty
(0 staged); all five source/test hashes matched the accepted bytes; the bundle root
`data/.cex002_harmonic_bundle` was absent (`test -e` exit 1) and not a dangling symlink
(`test -L` exit 1).

The three named checks were grouped in one terminal request with `set -e`:

```
set -e
.venv/bin/python -m pytest -q tests/catalog tests/ingest/test_binance_usdm_harmonic_bundle.py
  -> 149 passed (72 + 72 + 5; progress [48%]/[96%]/[100%])

.venv/bin/ruff check src/cryptofactors/ingest/binance_usdm_harmonic_bundle.py tests/ingest/test_binance_usdm_harmonic_bundle.py
  -> All checks passed!

.venv/bin/python scripts/check_repo_control.py
  -> Repo control check: PASS
```

## Integration

- Staged exactly three paths: the two changed source/test paths above plus this Record 505.
- `git diff --cached --check`: exit 0, no output.
- Staged path list and committed blob identities verified.
- Commit and normal push executed; HEAD equals origin/main and the index is empty.
- The full source integration commit is pinned by Record 506 (which executes the new
  preparation); it is recorded in this record's commit step and its five committed blobs
  were verified against the frozen hashes above.
- No `git add -A`, no unrelated staging, no amend/reset/force push.

## Scope limits and gaps

- No real prepare, publish, consumer or data operation occurred in this integration.
- Final release acceptance remains pending; this record claims integration only.
- The three unchanged paths (CLI and both catalog paths) were not modified.
- Unrelated working-tree changes and reviewer governance edits were preserved.

## Record status

Record 505 is implementation evidence owned by Hermes. CEX-002 remains IN_PROGRESS;
next ticket NONE; reviewer acceptance remains exclusive.
