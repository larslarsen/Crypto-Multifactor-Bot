# CEX-002 Retirement Targeted Failure and Descriptor Correction

- **Date:** 2026-08-27
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** targeted validation rejected; one consolidated descriptor-lifetime correction
- **Authorized actor:** Sr Dev - Grok Build XHigh
- **Gate 2:** in progress; rejected real store remains untouched
- **Next ticket:** `NONE`

## Integration result

Hermes integrated and pushed the exact Review-333 three-file source at commit
`f1c91f042fdcc1f13d8f26b98c7eb06bf59af8dc`. Focused Ruff passed with exit 0. The
targeted synthetic retirement-tool suite then ran once and stopped with exit 1 and five
failures:

- `test_symlink_is_rejected`;
- `test_special_file_is_rejected`;
- `test_replaced_inode_is_rejected`;
- `test_receipt_inode_replacement_after_inventory_is_rejected`; and
- `test_sqlite_inode_replacement_after_inventory_is_rejected`.

No rerun or repair is accepted. The integrated CLI remains accepted unchanged at SHA-256
`66faa5c6c411d433ff7d4d3e36815d9677c1974c08829f361535dd3b41503ef6`. The real
retirement CLI was not invoked and the rejected store remains outside this round.

## Reviewer diagnosis

The five failures have two causes.

First, the lock is opened before inventory. A lock symlink therefore reaches the generic
no-follow open error, while a FIFO reaches the generic non-regular-file error. Both are bounded
safe failures, but their messages do not satisfy the tests' explicit `symlink` and `special`
contract.

Second, each inode fixture unlinks the original before creating its replacement. The filesystem
may immediately reuse the released inode, so `test_replaced_inode_is_rejected` does not reliably
construct a different identity. More importantly, `_prove_tree` opens the plan receipt and
SQLite database only after `after_inventory`. Their scanned descriptors have already been
closed, so those two critical inodes can also be reused during the hook and appear unchanged.
That is a production descriptor-lifetime defect, not merely a test problem.

## Exact senior correction

Grok may edit only:

- `src/cryptofactors/acquisition/binance_usdm_harmonic_gate2_retirement.py`; and
- `tests/acquisition/test_binance_usdm_harmonic_gate2_retirement.py`.

Make one consolidated correction:

1. In `_prove_tree`, open the authority-selected plan receipt and `state.sqlite` through
   no-follow descriptors before the initial inventory scan. Register both with `_Descriptors`
   and keep them open through the entire inspect/retire operation. Do not open a replacement
   descriptor after `after_inventory` and treat it as the pinned object.
2. After inventory comparison and `after_inventory`, reopen each exact name no-follow and prove
   that it still names the already-held descriptor and that the held descriptor matches its
   exact inventory entry. Support the nested receipt path without weakening path-component
   no-follow checks. Run receipt and SQLite semantic proof on the held descriptors.
3. Preserve the existing lock-first ordering and lock lifetime. Give a lock symlink a bounded
   safe error containing `symlink`, and a non-regular lock a bounded safe error containing
   `special`, without following or blocking on an unsafe target and without weakening the
   lock-held proof.
4. Replace the unlink-then-create inode fixtures with a shared deterministic replacement helper:
   create a sibling regular file while the original still exists, prove its inode differs, set
   the required bytes/mode, and atomically `os.replace` it over the target. Use it in all three
   inode-replacement tests. Preserve their safe-error and no-transition assertions.
5. Keep the production authority constants, CLI, exit semantics, receipt schema, lock/no-replace
   transaction, durability operations, post-rename proof, standard-library-only boundary, and
   every unrelated test unchanged. Keep the files ASCII and Ruff-clean.

The correction must make replacement detection depend on descriptor continuity, not only an
inode value copied from an earlier scan. Do not solve the failures by weakening exception-class
assertions, deleting race hooks, accepting replacement, changing authority, or merely broadening
all message matches.

Do not run commands/tests, use Git, edit the CLI or governance, import acquisition code, or
touch the real store. Return the two SHA-256 values and line counts plus test-function count.

Integration, validation, real `inspect`/retirement, corrected planning, acquisition, later
gates, and next-ticket work remain unauthorized. Gate 2 remains `IN_PROGRESS`; next ticket
remains `NONE`.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly this review,
`docs/handoff/CURRENT_TASK.md`, and `tickets/CEX-002.md`. Developer source/test paths,
ignored state/data, and unrelated dirty work are excluded.
