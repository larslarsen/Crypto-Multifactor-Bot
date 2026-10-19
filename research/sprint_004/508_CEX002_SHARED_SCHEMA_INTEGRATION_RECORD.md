# CEX-002 Record 508 — Shared schema contracts integration

Ticket: CEX-002, IN_PROGRESS; next ticket NONE
Actor: Jr Dev — Hermes
Model: meituan/longcat-2.5-preview:free (Nous Portal), no reasoning override
Reviewer: Lead Quantitative Finance Researcher/Engineer
Governing: Review 507 `research/sprint_004/507_CEX002_SHARED_SCHEMA_SOURCE_AUTHORIZATION.md`, ADR-0038

## Outcome

Review 507's two-path shared-schema source drop was validated and integrated. Registry
contracts are canonical, bounded, hash-bound and required at every manifest/footer path;
field order/types/nullability and complete proof tokens remain enforced. The SQLite formula,
object cap, metadata allocation and reserve are unchanged; resource errors now expose exact
charged classes. The developer's separate 63-case result is distinguished below from
Hermes's own validation.

## Final source/test identities

| path | SHA-256 | lines | status |
| --- | --- | --- | --- |
| src/cryptofactors/catalog/dataset/cex002_reference_release.py | fed0d0ef49eb3704be577a378dfd12eb7e6876fc41fbfe9d6507e7ef5b83fe00 | 2237 | changed |
| tests/catalog/test_cex002_reference_release.py | 293f45157c94e9978e18aa0f6720cc68ab8c230c19524abe0cf9140a87acfc8a | 1261 | changed |
| src/cryptofactors/ingest/binance_usdm_harmonic_bundle.py | 1c9214d088c4279cf34e78c24d97a9bc14124491c27f5575edcca67c675cb48b | 1996 | unchanged (Review 504) |
| scripts/research/publish_binance_usdm_harmonic_bundle.py | cfb5b04f87226c9d1efbb39bbd04b634c40c7a20ddb868b8c6b3768d817b3fd9 | 102 | unchanged (Review 498) |
| tests/ingest/test_binance_usdm_harmonic_bundle.py | 867125b2c123349abe56caa1f8c5e8ec5cc8342dc1909cb4029d123af364f2e0 | 1383 | unchanged (Review 504) |

## Developer result (not Hermes's validation)

The same GPT-6 Sol High actor completed the two-path catalog schema-registry correction and
stopped. Its single authorized targeted pytest returned exit 0 with 63 passing progress
marks and printed the computed synthetic budget (charged total 4,475,019,201; leftover
13,232,150; manifest bytes 252,802,987; prepared/publication 8,388,608 each; proof
reservation 536,870,912; SQLite reservation 3,655,335,936; remainder 4,985,471,619). The
reviewer inspected the production and test diffs and independently verified the hashes.

## Hermes validation (exact commands and results)

Pre-checks: HEAD == origin/main == `de8ecee5ca904336b6d9278548d998aee8a0ee88`; index empty
(0 staged); all five source/test hashes matched the accepted bytes. The owned bundle root
legitimately exists (per Review 507, the earlier absent-root rule is superseded).

The three named checks were grouped in one terminal request with `set -e`:

```
set -e
.venv/bin/python -m pytest -q tests/catalog tests/ingest/test_binance_usdm_harmonic_bundle.py
  -> 162 passed (24 + 72 + 66; progress [44%]/[88%]/[100%]); the developer's synthetic
     budget JSON was printed during the run:
     {"charged_total": 4475019201, "leftover_bytes": 13232150, "manifest_bytes": 252802987,
      "metadata_files": 244499, "prepared_bytes": 8388608, "proof_reservation_bytes": 536870912,
      "publication_bytes": 8388608, "remainder": 4985471619, "representative_proof_bytes": 281881986,
      "sqlite_bytes": 3655335936, "synthetic_files": 423446, "tables": 178947}

.venv/bin/ruff check src/cryptofactors/catalog/dataset/cex002_reference_release.py tests/catalog/test_cex002_reference_release.py
  -> All checks passed!

.venv/bin/python scripts/check_repo_control.py
  -> Repo control check: PASS
```

## Integration

- Staged exactly three paths: the two changed catalog paths above plus this Record 508.
- `git diff --cached --check`: exit 0, no output.
- Staged path list and committed blob identities verified.
- Commit and normal push executed; HEAD equals origin/main and the index is empty.
- The full source integration commit is pinned by Record 509 (which executes the new
  preparation); it is recorded in this record's commit step and its five committed blobs
  were verified against the frozen hashes above.
- No `git add -A`, no unrelated staging, no amend/reset/force push.

## Scope limits and gaps

- No real prepare, publish, consumer or data operation occurred in this integration.
- The synthetic budget is a conservative representative scenario, not a measurement or
  acceptance of the eventual real candidate; its real guard remains final.
- Final release acceptance remains pending; this record claims integration only.
- The three unchanged paths were not modified.
- Unrelated working-tree changes and reviewer governance edits were preserved.

## Record status

Record 508 is implementation evidence owned by Hermes. CEX-002 remains IN_PROGRESS;
next ticket NONE; reviewer acceptance remains exclusive.
