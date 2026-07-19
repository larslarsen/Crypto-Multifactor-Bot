# REVIEW-0012 — LEG-001 FINAL ACCEPTANCE

**Ticket:** LEG-001 — Register legacy local files without accepting their claims
**Verdict / Status:** ACCEPTED
**Accepted implementation commit:** `009dd112e7dd722e9075467faa594af944983c56`
**Integration record:** `docs/reviews/LEG-001_INTEGRATION.md`
**Prior review:** none (first final review for LEG-001).
**Reviewer:** Senior Engineer
**Junior (Hermes) action:** documentation / control-plane record only. No code, schema,
or test changes.

## Blocking findings

None. LEG-001 is accepted with no blocking findings.

## Evidence

- `pytest tests/ingest/test_legacy_local.py` (15 tests: 10 Jr invariants + 4 Sr
  acceptance blockers + 1 strengthened v1.2.2 merge-key regression): **15 passed**.
- `ruff check src/cryptofactors/ingest/legacy_local.py tests/ingest/test_legacy_local.py`:
  **All checks passed!**
- `mypy --no-incremental src/cryptofactors/ingest/legacy_local.py tests/ingest/test_legacy_local.py`:
  **Success: no issues found in 2 source files**.
- `python3 scripts/check_repo_control.py`: **PASS**.
- Full suite: **254 passed, 1 warning**.
- The strengthened merge-key regression (`test_multilevel_merge_deterministic_binary_order`)
  fails on parent commit `b40fcae` (pre-fix v1.2.1 code lacks the binary-key merge),
  confirming it guards the accepted fix.

## Accepted invariants

1. **Registration does not imply acceptance** — legacy entries are recorded with an
   unverified provenance class (`LEGACY_UNKNOWN`); original bytes are never rewritten and
   raw data stays outside Git. The census is an observation, not validation.
2. **Source immutability / binary identity** — each FS object is keyed by exact binary
   identity (length-prefixed name segments); embedded newlines, slashes, and non-UTF-8
   names are preserved and reversible (`b64:` form). Duplicate binary identity raises
   `LegacyPathCollisionError`.
3. **No-escape descriptor-relative traversal** — walking uses `O_DIRECTORY|O_NOFOLLOW`
   re-opens per component via `dir_fd`; a directory swapped to an escaping symlink raises
   ELOOP and is never descended, so no entries outside the root are recorded.
4. **Reversible, collision-free path representation + deterministic order** — raw
   `b"\x80"` (`b64:gA==`) and a literal `b64:gA==` file (`b64:YjY0OmdBPT0=`) emit two
   distinct `relative_path` values; the final inventory orders by canonical binary
   identity, stable across scans (verified byte-identical).
5. **Zero-byte regular file size** — an empty regular file appears with `byte_size == 0`
   (not null / omitted).
6. **Output/work subtree exclusion before enqueue or hash** — the output dir and
   `.leg001-*` work dirs are excluded (`output_self` / `work_self`) before enqueue or hash,
   so pre-existing artifacts under the output tree never enter the census.
7. **Bounded directory iteration and streaming duplicates** — traversal streams entries
   via `/proc/self/fd` (no `os.listdir` materialization); duplicate reporting streams from
   SQL with all relative paths, no full per-hash path list in memory.
8. **Exclusive staged publication** — publication reserves an absent final dir under a
   no-clobber reservation; a second publisher into the same output raises
   `LegacyInventoryExistsError`. A mid-publish failure triggers rollback; a clean retry
   into a fresh output succeeds.
9. **Bounded memory external merge** — runs are spilled to disk and k-way merged by binary
   identity at every level (including intermediate levels), so memory stays bounded on
   large trees with deterministic output.

## Next ticket authorized

`NONE`.

## Disposition

LEG-001 is ACCEPTED at `009dd112e7dd722e9075467faa594af944983c56`. No production changes in
this record; documentation and control-plane sync only.
