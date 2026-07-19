# LEG-001 — Sr acceptance-fix drop (v1.2.1)

**Status:** Ready for Jr integration and test coverage  
**Production file:** `src/cryptofactors/ingest/legacy_local.py`  
**Scanner version:** 1.2.1

## Code changes (already in production file)

1. `_iter_dir_names(dir_fd)` — descriptor-relative streaming entry iteration via `/proc/self/fd/<fd>` (no `os.listdir` materialization).
2. `_name_to_display` — names starting with `b64:` are themselves base64-wrapped so raw `b"\x80"` (`b64:gA==`) cannot collide with a UTF-8 file named `b64:gA==`. Run sort key is binary identity, not display path.
3. Empty regular files keep `byte_size=0`.
4. `out_parts_prefix` / `work_parts_prefix` exclusion runs before enqueue, hash, or classification.
5. `_stream_duplicate_report` writes one path at a time from SQL cursors.

## Jr work (see tickets/LEG-001.md and docs/handoff/CURRENT_TASK.md)

- Integrate this production file if not already at 1.2.1.
- Encode the four acceptance blockers as tests in `tests/ingest/test_legacy_local.py`.
- Run the acceptance commands on the ticket.
- Report in `LEG-001_INTEGRATION.md` and stop.
