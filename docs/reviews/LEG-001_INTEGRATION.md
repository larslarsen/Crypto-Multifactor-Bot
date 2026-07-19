# LEG-001 — Implementation Handoff & Validation Evidence

**Ticket:** MAN-adjacent P0 — LEG-001 (Register legacy local files without
accepting their claims)
**Integrated implementation commit:** `feat(leg-001): add legacy filesystem census`
**Status:** IN_PROGRESS (awaiting Senior/Engineer review)
**Source of truth:** `tickets/LEG-001.md`, `docs/handoff/CURRENT_TASK.md`,
`docs/architecture/08_LEGACY_MIGRATION_PLAN.md`

## Deliverable integrated

- `src/cryptofactors/ingest/legacy_local.py` — bounded-memory recursive legacy
  filesystem census scanner (`LegacyLocalScanner`, `scan_legacy_root`).
- `src/cryptofactors/ingest/__init__.py` — LEG-001 exports merged onto the
  existing RAW-001 re-exports (no RAW-001 content dropped).

Source: Sr Dev Sandbox drop `LEG001_scanner_impl.zip`, inspected read-only in
`/tmp` (no `.git`, no caches/build artifacts, no unrelated changes). The
delivered `legacy_local.py` contained two integration defects, corrected in
this handoff (see Corrections).

## Corrections applied (integration defects found)

1. **Concurrent no-clobber publication race.** The delivered
   `_atomic_publish_bytes` used `dest.exists()` checks plus `os.rename`, which
   **overwrites** an existing destination on POSIX under a concurrent writer.
   Replaced with an O_EXCL-style hard link: after fsync of the temp file,
   `os.link(temp, dest)` is used. `os.link` refuses to overwrite an existing
   destination (raises `FileExistsError`), which is converted to
   `LegacyInventoryExistsError`. The temp file is unlinked in `finally`
   regardless of outcome. Proven by `test_concurrent_publish_no_clobber_under_race`
   (injected competing writer) and `test_two_concurrent_scans_no_clobber`
   (two real threads, barrier-synchronized; exactly one publishes, the other
   raises, no silent clobber).

2. **Unbounded in-RAM inventory sort.** The delivered `scan()` loaded every
   spool line into a `list[tuple[str, str]]` and `.sort()`-ed it in memory —
   memory grew with the number of files. Replaced with an **external merge
   sort**: spool is read in bounded runs (`run_records = 8192`), each run
   sorted and spilled to a temp run file; a k-way `heapq` merge streams into a
   merged temp file; `_atomic_publish_bytes` streams that file to the final
   destination in 1 MiB chunks. Peak memory is O(run_records), independent of
   tree size. Proven by `test_bounded_streaming_deterministic_on_large_tree`
   (5000 files, output sorted correctly).

3. **mypy type error (variable shadowing).** The cleanup loops reused the
   `child` name (earlier typed as `DirEntry` in the traversal loop) for `Path`
   entries, producing `assignment`/`attr-defined` errors. Renamed to `item`.

4. **Lint hygiene.** Removed unused `published` flag; renamed ambiguous `l`
   loop variables to `line`; removed unused `Iterable` import (kept `Mapping`,
   which is genuinely used).

## Validated invariants (tests/ingest/test_legacy_local.py, 12 tests)

1. Recursive census hashes regular files; emits canonical JSONL + summary.
2. Symlinks recorded but never followed (outside-root target not traversed).
3. Default exclusions cover `.git`, venvs, caches, `.env`, key files.
4. Mutating a file during hashing -> `error_changed`, digest discarded.
5. Duplicate content counted correctly (groups + path count).
6. Output located beneath the scanned root excludes itself.
7. Existing output files are never overwritten (single scan raises).
8. Concurrent publication is race-safe (O_EXCL link; raises, no clobber).
8b. Two concurrent scans: exactly one publishes, the other raises.
9. Summary `inventory_sha256` and `inventory_byte_size` match published JSONL.
10. Repeated scans of an unchanged tree produce identical inventory records.
11. Bounded streaming: 5000-file tree sorted deterministically (no in-RAM blowup).

## Validation commands & results

```
PYTHONPATH=src uv run pytest tests/ingest/test_legacy_local.py -q
  -> 12 passed

PYTHONPATH=src uv run ruff check \
  src/cryptofactors/ingest/legacy_local.py \
  src/cryptofactors/ingest/__init__.py \
  tests/ingest/test_legacy_local.py
  -> All checks passed!

PYTHONPATH=src uv run mypy \
  src/cryptofactors/ingest/legacy_local.py \
  src/cryptofactors/ingest/__init__.py \
  tests/ingest/test_legacy_local.py --no-incremental
  -> Success: no issues found in 3 source files

python3 scripts/check_repo_control.py
  -> Repo control check: PASS
```

## Unresolved risks / notes

- The configured temporary area (`out`) **must remain on the same filesystem**
  as the final dataset store for the hard-link publish to be atomic. Cross-
  device `os.link` raises `OSError` (EXDEV). This is documented as a
  non-blocking configuration note; a future enhancement could fall back to a
  rename when link is impossible, but that would re-introduce the overwrite
  window, so it is intentionally not auto-applied.
- Full-repo mypy still has pre-existing errors outside LEG-001 (legacy of
  earlier tickets); not in scope.
- No CLI / catalog publication / migration logic added, per ticket scope.
- LEG-001 remains IN_PROGRESS; next ticket authorized: NONE.
