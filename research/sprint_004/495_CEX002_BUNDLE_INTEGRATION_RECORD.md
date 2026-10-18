# CEX-002 Record 495 — Harmonic reference release adapter integration

Ticket: CEX-002, IN_PROGRESS; next ticket NONE
Actor: Jr Dev — Hermes
Model: meituan/longcat-2.5-preview:free (Nous Portal), no reasoning override
Reviewer: Lead Quantitative Finance Researcher/Engineer
Governing: Review 494 `research/sprint_004/494_CEX002_BUNDLE_CORRECTION_HANDOFF.md`, ADR-0037

## Outcome

Review 494's final five-path bundle/reference-catalog correction was validated and
integrated. The developer's targeted pytest (26/2, then 28 passing) is distinguished below
from Hermes's own validation. One import-only source correction was applied by the source
actor after an initial scoped-Ruff failure. No real prepare/publish/consumer/data operation
occurred, and final release acceptance remains pending.

## Final five source/test identities (integrated bytes)

| path | SHA-256 | lines |
| --- | --- | --- |
| src/cryptofactors/catalog/dataset/cex002_reference_release.py | 942140dbbc85a4b7cb7f24284442edf8b8289705651895be7cdaa076ddaa8387 | 2139 |
| src/cryptofactors/ingest/binance_usdm_harmonic_bundle.py | dedf31e1996a71c055560b40558a6f1e2a86f8429da805d4cf17a02caf87355e | 1848 |
| scripts/research/publish_binance_usdm_harmonic_bundle.py | d245e6195f5619a3d2c5594bb3a1edf4a5345b2696486a352b5af398b3681553 | 101 |
| tests/catalog/test_cex002_reference_release.py | e4d7cf4335e87d8e7bb4ecb2f87dd106f601e845c47e369f095a784fe3c5f456 | 1020 |
| tests/ingest/test_binance_usdm_harmonic_bundle.py | d33da132d17026b3042aa26f8142f6ba6fe8758c2377705b96141d46a1102d1a | 1088 |

The catalog test was `c043dcc63fce6e2c7366cdf2365c0af96b39d26a9203455be0e493132585e1a2`
(1021 lines) before the source actor's import-only correction; the reviewer independently
verified that re-inserting exactly the removed line reproduces that earlier hash.

## Developer history (not Hermes's validation)

- Review 494 prepared the consolidated five-path repair for GPT-6 Sol High.
- Developer's first correction run: exit 1, 26 passed / 2 failed; stopped.
- Review 494 final section authorized two test-fixture selection corrections, then one
  additional execution of the same two-file pytest.
- Developer's continuation run: exit 0, all 28 cases passing.
- The developer's focused pytest command was NOT repeated by Hermes as a separate step;
  the catalog regression command below includes it.

## Hermes validation (exact commands and results)

Pre-checks: index empty (0 staged); five files matched their accepted hashes before
validation.

```
.venv/bin/python -m pytest -q tests/catalog tests/ingest/test_binance_usdm_harmonic_bundle.py
  -> exit 0; 127 progress dots (catalog regression includes the developer's focused run)
```

```
.venv/bin/ruff check src/cryptofactors/catalog/dataset/cex002_reference_release.py src/cryptofactors/ingest/binance_usdm_harmonic_bundle.py scripts/research/publish_binance_usdm_harmonic_bundle.py tests/catalog/test_cex002_reference_release.py tests/ingest/test_binance_usdm_harmonic_bundle.py
  -> FIRST RUN exit 1: "Found 3 errors." F401 unused imports
     (`datetime.datetime`, `datetime.timedelta`, `datetime.timezone`) at
     tests/catalog/test_cex002_reference_release.py:12.
```

The initial scoped-Ruff failure stopped the workflow at that point. No repair or retry was
performed by Hermes. The same GPT-6 Sol source actor then removed ONLY the single
`from datetime import datetime, timedelta, timezone` line in
tests/catalog/test_cex002_reference_release.py and stopped; the reviewer independently
verified the re-insertion reproduces the prior hash.

```
.venv/bin/ruff check <the same five paths>
  -> RESUMED RUN exit 0: "All checks passed!"
```

```
.venv/bin/python scripts/check_repo_control.py
  -> exit 0: "Repo control check: PASS"
```

## Integration

- Staged exactly six paths: the five source/test files above plus this Record 495.
- `git diff --cached --check`: exit 0, no output.
- Staged path list and source identities verified.
- Commit and normal push executed; HEAD equals origin/main and the index is empty.
- No `git add -A`, no unrelated staging, no amend/reset/force push.

## Scope limits and gaps

- No real prepare, publish, consumer or data operation occurred in this integration.
- Final release acceptance remains pending; this record claims integration only.
- The three production/CLI paths were not modified by this workflow.
- Unrelated working-tree changes and reviewer governance edits were preserved.

## Record status

Record 495 is implementation evidence owned by Hermes. CEX-002 remains IN_PROGRESS;
next ticket NONE; reviewer acceptance remains exclusive.
