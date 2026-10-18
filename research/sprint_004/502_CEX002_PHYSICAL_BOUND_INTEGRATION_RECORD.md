# CEX-002 Record 502 — Physical inventory bound integration

Ticket: CEX-002, IN_PROGRESS; next ticket NONE
Actor: Jr Dev — Hermes
Model: meituan/longcat-2.5-preview:free (Nous Portal), no reasoning override
Reviewer: Lead Quantitative Finance Researcher/Engineer
Governing: Review 501 `research/sprint_004/501_CEX002_PHYSICAL_INVENTORY_BOUND_CORRECTION.md`, ADR-0037

## Outcome

Review 501's two-path derived-bound correction was validated and integrated. The fix
derives each product's physical-file cap from the accepted descriptor-path count plus that
product's frozen retained-kind allowance; all existing classification, digest and symlink
rules remain. The synthetic walk test permits exactly 65,635/65,651 files and rejects the
next regular file for each product without physical data creation. There is no public
bypass or unexplained slack. The developer's separate 37-case result is distinguished below
from Hermes's own validation.

## Final source/test identities

| path | SHA-256 | lines | status |
| --- | --- | --- | --- |
| src/cryptofactors/ingest/binance_usdm_harmonic_bundle.py | 1370c63017275692c4b43c8577bcee8c3475ea357bf041a446a6ccec4debd3e5 | 1925 | changed |
| tests/ingest/test_binance_usdm_harmonic_bundle.py | e91ac496b1de969b975c0dd95b3ef0c79340d7b0ed8f0ce6310761e917baf1b4 | 1239 | changed |
| scripts/research/publish_binance_usdm_harmonic_bundle.py | cfb5b04f87226c9d1efbb39bbd04b634c40c7a20ddb868b8c6b3768d817b3fd9 | 102 | unchanged (Review 498) |
| src/cryptofactors/catalog/dataset/cex002_reference_release.py | 942140dbbc85a4b7cb7f24284442edf8b8289705651895be7cdaa076ddaa8387 | 2139 | unchanged (Review 495) |
| tests/catalog/test_cex002_reference_release.py | e4d7cf4335e87d8e7bb4ecb2f87dd106f601e845c47e369f095a784fe3c5f456 | 1020 | unchanged (Review 495) |

## Developer result (not Hermes's validation)

The same GPT-6 Sol High author completed the two-path derived-bound fix and stopped. Its
single authorized targeted pytest returned exit 0 with 37 passing cases. The reviewer
independently verified the exact diff and hashes. Review 501 corrects the copied off-by-one
total: the accepted closure 45,269 plus the retained inventories gives 65,635 bar / 65,651
flow (Record 459's component counts sum to 65,651, not 65,650).

## Hermes validation (exact commands and results)

Pre-checks: HEAD == origin/main == `b57fa7bc5fe1601decc8084c54c3b874bcf47f51`; index empty
(0 staged); all five source/test hashes matched the accepted bytes; the bundle root
`data/.cex002_harmonic_bundle` was absent (`test -e` exit 1) and not a dangling symlink
(`test -L` exit 1).

```
.venv/bin/python -m pytest -q tests/catalog tests/ingest/test_binance_usdm_harmonic_bundle.py
  -> exit 0; 136 passed (64 + 72; progress [52%]/[100%])
```

```
.venv/bin/ruff check src/cryptofactors/ingest/binance_usdm_harmonic_bundle.py tests/ingest/test_binance_usdm_harmonic_bundle.py
  -> exit 0; All checks passed!
```

```
.venv/bin/python scripts/check_repo_control.py
  -> exit 0; Repo control check: PASS
```

## Integration

- Staged exactly three paths: the two changed source/test paths above plus this Record 502.
- `git diff --cached --check`: exit 0, no output.
- Staged path list and committed blob identities verified.
- Commit and normal push executed; HEAD equals origin/main and the index is empty.
- The full source integration commit is recorded in this record's commit step; the five
  committed blobs at that commit match the frozen hashes above.
- No `git add -A`, no unrelated staging, no amend/reset/force push.

## Scope limits and gaps

- No real prepare, publish, consumer or data operation occurred in this integration.
- Final release acceptance remains pending; this record claims integration only.
- The three unchanged paths (CLI and both catalog paths) were not modified.
- Unrelated working-tree changes and reviewer governance edits were preserved.

## Record status

Record 502 is implementation evidence owned by Hermes. CEX-002 remains IN_PROGRESS;
next ticket NONE; reviewer acceptance remains exclusive.
