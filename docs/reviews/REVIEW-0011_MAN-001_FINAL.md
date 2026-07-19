# REVIEW-0011 — MAN-001 FINAL ACCEPTANCE

**Ticket:** MAN-001 — Dataset manifest fingerprint and publisher
**Verdict / Status:** ACCEPTED
**Accepted implementation commit:** `1ee869766341d91f1b29a5fb2acc731c984855da`
**Integration record:** `docs/reviews/MAN-001_INTEGRATION.md`
**Prior review:** REVIEW-0010 (CHANGES_REQUIRED) — 7 defects (D1–D7) corrected by the
accepted implementation commit above.
**Reviewer:** Senior Engineer
**Junior (Hermes) action:** documentation / control-plane record only. No code, schema,
or test changes.

## Blocking findings

None. All seven defects from REVIEW-0010 are resolved and validated.

## Evidence

- Full suite: **239 passed, 1 warning**.
- Final targeted tests (correction + dataset-manifest + duplicate-content + migration-acceptance):
  **58 passed**.
- `mypy` (affected, `--no-incremental`): **Success — no issues in 18 source files**.
- `ruff check src tests scripts`: **All checks passed!**
- Wheel build: `crypto_multifactor_bot-0.1.0-py3-none-any.whl` built successfully.
- `python3 scripts/check_repo_control.py`: **PASS**.

## Accepted invariants

1. **Immutable independent output bytes** — published outputs are copied to a new inode
   (never hard-linked); rewriting or deleting the caller's source cannot corrupt published data.
2. **Staged atomic publication** — publication builds in a unique temp stage under
   `config.temp_dir()`, fsyncs, then atomically `os.rename`s into an absent final dir under a
   no-clobber reservation; a pre-existing (incl. empty) final dir is never overwritten.
3. **Safe concurrent convergence** — concurrent identical publishers converge on exactly one
   dataset tree and one catalog row; the loser reuses the completed identical tree.
4. **Strict manifest / schema agreement** — the Pydantic `DatasetManifestWire` model is the
   single source of truth; `schemas/dataset_manifest.schema.json` is generated from it and
   validated in `manifest_from_dict` (fail-closed on unknown / missing / malformed / coerced fields).
5. **Exact catalog idempotence** — `_complete_identical_registration` and `verify_dataset`
   compare every persisted field exactly (incl. `publication_status`, `quality_summary_json`,
   coverage/availability times, `created_at`, `supersedes_dataset_id`, file `partition_json`).
6. **Fail-closed receipt / tree verification** — `verify_published_tree(receipt)` independently
   verifies the on-disk tree before the catalog transaction; fabricated, deleted, or mutated
   trees are rejected with `CorruptDatasetError`.

## Non-blocking configuration note

The configured temporary build area (`DatasetStoreConfig.temp_dir()`) MUST remain on the
**same filesystem** as the final dataset store root. Atomic directory publication relies on
`os.rename`, which is atomic only within a single filesystem; a cross-device temp dir would
force a copy + delete and break the no-partial-final-dir guarantee.

## Next ticket authorized

`LEG-001` — NOT activated or implemented by this record.

## Disposition

MAN-001 is ACCEPTED at `1ee869766341d91f1b29a5fb2acc731c984855da`. No production changes in
this commit; documentation and control-plane sync only.
