# CEX-002 Retirement Tool Static Review and Consolidated Correction

- **Date:** 2026-08-27
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** first retirement-tool drop rejected; one consolidated correction authorized
- **Authorized actor:** Sr Dev - Grok Build XHigh
- **Gate 2:** in progress; rejected real store remains untouched
- **Next ticket:** `NONE`

## Reviewed identities

The reviewer inspected Grok's three-file Review-330 return once without running commands or
tests:

- module SHA-256 `d5d7e727ca6392183926f1cacdcddcac2704fa7fda4bc183430d70a0089a5f73`,
  1,649 lines;
- CLI SHA-256 `d298ab9c5609d972198fdc0e0164a5facd26d71b6205282d7d773bdde089ef5c`,
  72 lines; and
- test SHA-256 `970665ca3d404823ba99cd854e532b80b3e1b2733d99eea75e06e6ab4e1e2e68`,
  1,229 lines and 49 test functions.

Only the three authorized paths changed. The authority JSON, accepted acquisition files,
governance, and real Gate-2 tree remain unchanged. No test result is accepted.

## Accepted foundation

Preserve the standalone standard-library boundary, fixed production authority/path/confirmation,
closed-schema authority, descriptor-relative no-follow inventory, streaming hashes, existing
nonblocking acquisition lock, immutable query-only SQLite semantics, exact database facts,
Linux `renameat2(RENAME_NOREPLACE)`, both rename-parent `fsync`s, filesystem `syncfs`, complete
post-inventory, bounded receipts, distinct pre/post-rename failures, and the useful synthetic
fixture structure. Do not rewrite the design or acquisition code.

## Blocking findings

### 1. The renamed names are not rebound to the proved descriptors

The module proves and locks an opened `gate2` descriptor, but the actual syscall later renames
the current `gate2` name without immediately proving that the name still has the opened root's
device and inode. A replacement race can therefore move a different tree while the tool holds
the old tree's lock. Post-proof detects the wrong inode only after mutation.

The new `gate2_retired` descriptor has the symmetric defect: its name can be detached/replaced
before the rename, while the syscall targets the still-open but no-longer-named directory.
Post-proof walks only that descriptor and does not prove that the fixed parent name still
resolves to it. The plan receipt and SQLite state are also reopened by names after inventory
without rebinding their descriptors to the authority inode before semantic use.

Correct this with one reusable no-follow name-to-descriptor identity proof. Before semantic
use, open the receipt and SQLite file no-follow, require their full expected inventory identity,
and open SQLite through the already-proved state-file descriptor using
`mode=ro&immutable=1`. Immediately before `renameat2`, prove:

- the active name resolves to the held active-root descriptor;
- the lock name resolves to the held locked descriptor; and
- the retirement-parent name resolves to the opened 0700 same-device parent descriptor.

After rename, prove the retirement-parent name still resolves to that descriptor and the
destination name resolves to the post-proof destination descriptor. No path-based semantic
reopen may float away from its inventoried inode. Add narrow `after_inventory` and
`before_rename` hooks if needed for deterministic tests; production defaults do nothing.

### 2. Successful mutation can be falsely reported as exit 0 without a delivered receipt

The CLI catches `BrokenPipeError` and returns `EXIT_COMPLETE`. It also writes to buffered stdout
without an explicit flush. A retirement can therefore complete durably while receipt delivery
fails, yet the process reports success. Serialize once, write, and explicitly flush. For
`retire`, any write/flush failure after the function returns must emit a bounded stderr error
and return `EXIT_INDETERMINATE`, never 0 and never retry the transition. Read-only `inspect`
output failure returns a nonzero safe/output failure. Add CLI tests for write and flush failure
and normal exact output.

### 3. Corrupt SQLite escapes the safe failure contract

`prove_sqlite` lets several `sqlite3.Error` paths from malformed/corrupt state escape as raw
exceptions. The CLI then produces a traceback/usage-style failure instead of the required
bounded pre-rename safe result. Preserve an existing `SafeRetirementError`, but translate all
other SQLite query/open/close and row-shape failures into a bounded `SafeRetirementError` while
the rename is still impossible. Never treat an arbitrary SQLite error from the write probe as
proof of read-only mode: require the connection's query-only state and distinguish the expected
read-only write rejection from corruption/other failure. The corrupt-database test must reach
and assert this bounded safe path.

### 4. Residual test and lint defects

The foreign-key fixture tries to disable enforcement inside an active transaction; SQLite
ignores that change, so fixture construction can fail before the retirement assertion. Commit
before disabling foreign keys (or otherwise construct the orphan outside an active enforced
transaction), then confirm `foreign_key_check` observes the intended violation.

Add tests for active-root replacement, retirement-parent replacement before and after rename,
receipt/state inode replacement after inventory, pre-rename store-parent `fsync` failure, and
the receipt-output failures above. Add one offline test proving the committed production
authority bytes match `AUTHORITY_SHA256` and authenticate without touching the real store.
Strengthen the immutable-SQLite test to observe the tool's descriptor URI/query-only behavior,
not a separate connection created by the test.

Remove the unused production `errno` import and unused create-path branch, replace the new
non-ASCII dash, and wrap the two lines over the configured line ceiling. Preserve ASCII and
Ruff-clean formatting throughout.

## Stop boundary

Grok may edit only the same three Review-330 paths. Do not run commands/tests, use Git, edit the
authority or governance, import acquisition code, or touch the real store. Return once with
the three SHA-256 values and line counts plus test-function count.

Integration, validation, real `inspect`, retirement, corrected planning, acquisition, network
access, later gates, and next-ticket work remain unauthorized. Gate 2 remains `IN_PROGRESS`;
next ticket remains `NONE`.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly this review,
`docs/handoff/CURRENT_TASK.md`, and `tickets/CEX-002.md`. Developer source/test paths,
ignored state/data, and unrelated dirty work are excluded.
