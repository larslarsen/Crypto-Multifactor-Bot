# LEG-001 — Implementation Handoff & Validation Evidence

**Ticket:** LEG-001 (Register legacy local files without accepting their claims)
**Status:** IN_PROGRESS (awaiting owner/reviewer acceptance)
**Source of truth:** `tickets/LEG-001.md`, `docs/handoff/CURRENT_TASK.md`,
`docs/architecture/08_LEGACY_MIGRATION_PLAN.md`, `AGENTS.md`

## Deliverable integrated (Sr Dev Sandbox, v1.2.1)

- `src/cryptofactors/ingest/legacy_local.py` — bounded-memory recursive legacy
  filesystem census scanner (`LegacyLocalScanner`, `scan_legacy_root`),
  scanner version `1.2.1`.
- `src/cryptofactors/ingest/__init__.py` — LEG-001 exports merged onto the
  existing RAW-001 re-exports (RAW-001 content preserved, verified).

Source: Sr Dev Sandbox drop `LEG001_v121_repo_directive.zip` (newest in
`~/Downloads`, dropped after the v1.2.0 push). Inspected read-only; contains
`legacy_local.py` (v1.2.1), the updated `tickets/LEG-001.md`, `CURRENT_TASK.md`,
and `LEG-001_SR_ACCEPTANCE_FIXES.md`. Supersedes `LEG001_v12_corrected.zip`
(v1.2.0). v1.2.1 adds: descriptor-relative streaming directory iteration via
`/proc/self/fd` (no `os.listdir` materialization), `b64:` self-wrapping so a raw
`b"\x80"` (`b64:gA==`) stays distinct from a literal `b64:gA==` file
(`b64:YjY0OmdBPT0=`), zero-byte regular-file `byte_size`, and output/work
subtree exclusion (`output_self`/`work_self`) before enqueue or hash.

## Integration defects fixed (in the Sr v1.2.0 code, to pass repo gates)

The raw Sr drop did not pass the repository's `strict = true` mypy gate and had
two ruff findings. Minimal, behavior-preserving fixes applied to
`legacy_local.py`:

1. `handles` annotation in `_merge_runs` — declared `list[io.TextIOWrapper]`
   (matches `Path.open()`'s return) instead of the incompatible `TextIO` alias.
   Added `import io` (carried over from v1.1.0 integration).
2. Lint hygiene: removed unused `collections.abc.Iterator` import and a dead
   `root_id = _stat_identity(os.fstat(root_fd))` assignment in `scan()`.

No behavioral logic was altered; the Sr scanner's invariants are intact.

## Exact test inventory — `tests/ingest/test_legacy_local.py` (14 tests)

Mapped to the required Jr validation focus (1-10) and the Sr v1.2.1 acceptance
blockers (11-14):

1. `test_embedded_newline_name_unique` — filename with embedded newline survives
   and is its own unique inventory entry (reversible `b64:` form).
2. `test_non_utf8_name_b64_display` — non-UTF-8 name -> `b64:` display; JSONL
   contains no surrogate code points (verified char-by-char); payload decodes
   back to the exact raw bytes.
3. `test_path_collision_binary_identity` — duplicate binary-identity key in the
   `seen` PRIMARY KEY -> `LegacyPathCollisionError` (IntegrityError conversion).
4. `test_symlink_swap_mid_hash_error_changed` — fstat identity changes between
   pre/post-hash -> `ERROR_CHANGED`, no sha recorded.
5. `test_symlink_dir_swap_no_escape` — a directory swapped to an escaping
   symlink mid-traversal raises ELOOP; `O_DIRECTORY|O_NOFOLLOW` re-open prevents
   any escape outside root (no outside entries; child never scanned; failure
   surfaced as `error_unreadable`/`error_symlink`).
6. `test_overlong_full_identity_retained` — overlong path -> `ERROR_OVERLONG`
   record with full (non-truncated) identity retained.
7. `test_work_stage_dirs_excluded` — `.leg001-*` work/stage dirs never appear in
   the census (recorded `skipped_excluded`, never hashed).
8. `test_duplicate_report_streams_and_counts_match` — duplicate report streams
   from SQL; `duplicate_hash_groups` / `duplicate_path_count` match the report.
9. `test_concurrent_no_clobber_and_rollback_retry` — second publisher into the
   same output -> `LegacyInventoryExistsError`; a mid-publish `os.link` failure
   triggers rollback; a clean retry into a fresh output succeeds.
10. `test_bounded_streaming_on_large_tree` — 5000-file tree: streaming produces
    multiple bounded run files (no full in-RAM buffer); inventory is complete
    and sorted.
11. `test_bounded_iteration_and_streaming_duplicates` — Sr acceptance blocker 1:
    1000-entry directory census completes (no `os.listdir` materialization);
    repeated content hash appears in the duplicate report with all paths.
12. `test_b64_self_wrap_distinct_and_deterministic_order` — Sr acceptance blocker
    2: raw `b"\x80"` (`b64:gA==`) and literal `b64:gA==` (`b64:YjY0OmdBPT0=`) emit
    two distinct `relative_path` values; inventory bytes identical across scans.
13. `test_zero_byte_regular_file_size` — Sr acceptance blocker 3: empty regular
    file appears with `byte_size == 0` (not null/omitted).
14. `test_output_subtree_excluded_before_enqueue` — Sr acceptance blocker 4:
    `legacy_root/out/preexisting.txt` with `output_dir=legacy_root/out` is absent
    from the inventory; `excluded_by_rule["output_self"]` records the exclusion.

## v1.2.1 integration defect fixed (to pass repo gates)

The raw v1.2.1 drop did not pass `strict = true` mypy / ruff. Minimal,
behavior-preserving fixes applied to `legacy_local.py`:

1. `run_buffer` / `_write_sorted_run` annotation — v1.2.1 sorts runs by binary
   identity key (`tuple[bytes, str]`); the inherited display-key type
   (`tuple[str, str]`) caused an `arg-type` error. Updated both to
   `tuple[bytes, str]`.
2. Lint hygiene: removed a dead `root_id = _stat_identity(os.fstat(root_fd))`
   assignment re-introduced in the v1.2.1 drop.

No behavioral logic was altered; the Sr scanner's invariants are intact.

## Validation commands & results

```
# Exact acceptance commands (tickets/LEG-001.md):
PYTHONPATH=src uv run pytest tests/ingest/test_legacy_local.py -q --tb=short
  -> 14 passed

PYTHONPATH=src uv run ruff check src/cryptofactors/ingest/legacy_local.py tests/ingest/test_legacy_local.py
  -> All checks passed!

PYTHONPATH=src uv run mypy --no-incremental src/cryptofactors/ingest/legacy_local.py tests/ingest/test_legacy_local.py
  -> Success: no issues found in 2 source files

python3 scripts/check_repo_control.py
  -> Repo control check: PASS

# Full suite (context):
PYTHONPATH=src uv run pytest -q
  -> 253 passed
```

## Unresolved risks / notes

- Same-filesystem assumption for atomic link (consistent with MAN-001): the
  publish reservation hard-links staged -> final; cross-device `os.link` falls
  back to an `O_EXCL` copy, re-raising `LegacyInventoryExistsError` on EEXIST.
- `scandir`/listdir order is non-deterministic; the final inventory is sorted
  externally (bounded external merge sort), so output is deterministic.
- On platforms without `openat`/`O_NOFOLLOW`, the scanner falls back to
  path-based `open` with best-effort stat-identity checks (weaker TOCTOU only
  where the OS omits the descriptor-relative APIs).
- Full-repo mypy outside LEG-001 (legacy of earlier tickets) is out of scope.
- No CLI / catalog publication / migration logic added, per ticket scope.
- LEG-001 remains IN_PROGRESS; next ticket authorized: NONE.
