# LEG-001 — Implementation Handoff & Validation Evidence

**Ticket:** LEG-001 (Register legacy local files without accepting their claims)
**Status:** IN_PROGRESS (awaiting owner/reviewer acceptance)
**Source of truth:** `tickets/LEG-001.md`, `docs/handoff/CURRENT_TASK.md`,
`docs/architecture/08_LEGACY_MIGRATION_PLAN.md`, `AGENTS.md`

## Deliverable integrated (Sr Dev Sandbox, v1.1.0)

- `src/cryptofactors/ingest/legacy_local.py` — bounded-memory recursive legacy
  filesystem census scanner (`LegacyLocalScanner`, `scan_legacy_root`),
  scanner version `1.1.0`.
- `src/cryptofactors/ingest/__init__.py` — LEG-001 exports merged onto the
  existing RAW-001 re-exports (RAW-001 content preserved, verified).

Source: Sr Dev Sandbox drop `LEG001_corrected.zip` (located in `~/Downloads`,
dropped after the prior push). Inspected read-only; contains only the two
`ingest/` files (no `.git`, caches, or build artifacts, no unrelated changes).
This corrected drop supersedes the earlier `LEG001_scanner_impl.zip` (v1.0.0)
and natively implements every symbol in the required test spec
(`LegacyPathCollisionError`, `LegacyConfigError`, `ERROR_OVERLONG`,
`O_NOFOLLOW` descriptor-relative no-follow hashing, `output_dir == legacy_root`
rejection, etc.).

## Integration defects fixed (in the Sr v1.1.0 code, to pass repo gates)

The raw Sr drop did not pass the repository's `strict = true` mypy gate. Two
minimal, behavior-preserving type fixes were applied to `legacy_local.py`:

1. `handles` annotation in `_merge_runs` — declared `list[io.TextIOWrapper]`
   (matches `Path.open()`'s return) instead of the incompatible `TextIO`
   alias. Added `import io`.
2. Cleanup-loop variable in `LegacyLocalScanner.scan` `finally` — renamed the
   `child` loop variable to `item` to clear a stale `DirEntry`/`Path` shadow
   false positive.

No behavioral logic was altered; the Sr scanner's invariants are intact.

## Exact test inventory — `tests/ingest/test_legacy_local.py` (15 tests)

Mapped 1:1 to the required invariants:

1. `test_filename_whitespace_preserved_distinctly` — leading/trailing spaces in
   filenames preserved distinctly (no trim/collapse).
2. `test_path_collision_raises` — two entries collapsing to one logical rel ->
   `LegacyPathCollisionError` (exercises the `seen` PRIMARY KEY ->
   IntegrityError -> `LegacyPathCollisionError` conversion deterministically).
3. `test_symlink_swap_mid_hash_error_changed` — symlink/dir-entry swap during
   hash -> `ERROR_CHANGED`, no external bytes read.
4. `test_onofollow_symlink_not_hashed` — O_NOFOLLOW-directed path: symlink
   recorded `error_symlink`, never hashed.
5. `test_output_basename_rejects_separators` — `/`, `\`, `.`, `..`, absolute
   basenames -> `LegacyConfigError`.
6. `test_output_dir_equals_root_rejected` — `output_dir == legacy_root` ->
   `LegacyConfigError`.
7. `test_output_subtree_under_root_excluded` — output subtree under root not
   scanned (self-exclusion).
8. `test_overlong_path_recorded` — overlong path -> `ERROR_OVERLONG` record +
   summary count.
9. `test_typed_status_records_present` — unreadable/special/symlink -> typed
   status records (`error_symlink`, `error_special`).
10. `test_duplicate_content_reported` — duplicate content -> duplicate report
    group + summary counts (`duplicate_hash_groups`, `duplicate_path_count`).
11. `test_no_clobber_second_scan_raises` — second scan -> `LegacyInventoryExistsError`.
12. `test_partial_failure_cleanup_allows_retry` — partial-failure cleanup leaves
    no temp artifacts that block a clean retry.
13. `test_deterministic_inventory_bytes` — deterministic inventory byte identity
    (ignores `scanned_at_utc`).
14. `test_heuristic_never_verified_provenance` — heuristics never yield
    `VERIFIED_*` provenance.

(One test skips when `os.mkfifo`/FIFO support is unavailable on the platform.)

## Validation commands & results

```
PYTHONPATH=src uv run pytest tests/ingest/test_legacy_local.py -q
  -> 15 passed (1 skipped on platforms without mkfifo)

PYTHONPATH=src uv run pytest -q        # full suite
  -> 256 passed, 1 skipped

PYTHONPATH=src uv run ruff check src/cryptofactors/ingest/legacy_local.py \
  src/cryptofactors/ingest/__init__.py tests/ingest/test_legacy_local.py
  -> All checks passed!

PYTHONPATH=src uv run mypy --no-incremental \
  src/cryptofactors/ingest/legacy_local.py \
  src/cryptofactors/ingest/__init__.py tests/ingest/test_legacy_local.py
  -> Success: no issues found in 3 source files

python3 scripts/check_repo_control.py
  -> Repo control check: PASS
```

## Unresolved risks / notes

- Same-filesystem assumption for atomic rename/link (consistent with MAN-001):
  the publish reservation hard-links temp -> dest on the same filesystem;
  cross-device `os.link` raises EXDEV, handled as a publish failure (no
  overwrite window re-opened).
- `scandir` iteration order is non-deterministic; the final inventory is sorted
  externally (bounded external merge sort), so output is deterministic.
- On platforms without `openat`/`O_NOFOLLOW`, the scanner falls back to
  path-based `open` with best-effort stat-identity checks (TOCTOU still
  mitigated where `O_NOFOLLOW` exists; weaker only where the OS omits it).
- Full-repo mypy outside LEG-001 (legacy of earlier tickets) is out of scope.
- No CLI / catalog publication / migration logic added, per ticket scope.
- LEG-001 remains IN_PROGRESS; next ticket authorized: NONE.
