# CEX-002 Gate-2 Retirement Tool Architecture and Source Authorization

- **Date:** 2026-08-27
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** targeted suite accepted; exact rejected-store authority recorded; standalone retirement tool authorized
- **Authorized actor:** Sr Dev - Grok Build XHigh
- **Gate 2:** in progress; no raw acquisition fact exists
- **Next ticket:** `NONE`

## Accepted state

Hermes integrated Spark's exact fixture correction in pushed commit
`6e7ed863a6478a4a5a2967a23d44c5199b225a17`. The commit changes only the acquisition test by
the accepted three lines, `HEAD == origin/main`, and the accepted identities are:

- acquisition source SHA-256
  `af6ef568b9f0f30827b393efc013b13560d4fd5761ec86417c0d2cf461e1248d`;
- acquisition test SHA-256
  `40a75c4e8516f94e9d7528ec036bd7fef964219ac2203768f510364ff30d2624`;
  and
- CLI SHA-256
  `6f4b56ecb43dcc448eb6c8cf765e38d9fa3923432459574d913582e3d9c84043`.

Hermes reports the one authorized targeted acquisition suite passed. The reviewer accepts that
result without rerunning it. The complete ADR-0030 retained-authority correction is accepted.

## Rejected-store proof

The reviewer inspected the rejected store without importing the acquisition module and
published the exact machine-readable authority at:

- `research/sprint_004/330_CEX002_REJECTED_GATE2_RETIREMENT_AUTHORITY.json`;
- SHA-256 `8c658629a8adcb4eecd46b84509221f83bb053dc916a83f546e4de8e14a4ebc1`;
- 6,167 bytes.

It binds all ten tree entries by relative path, type, device, inode, mode, size, and regular-file
SHA-256. The tree is 742,380,087 regular-file bytes: one 742,342,656-byte SQLite plan database,
one 4,663-byte plan receipt, a 32,768-byte SHM file, an empty WAL, an empty acquisition lock,
and four empty child directories. Every entry is on device 64513. The fixed retirement parent
and destination are absent.

Immutable read-only SQLite inspection proves 737,119 plan rows, 90 retained labels, 202
`unsupported_mapping` gaps, one exact unfinished run, and zero attempts, completions,
sidecars, charges, charge transitions, publications, seals, network calls, errors, or acquired
bytes. The initial seal head has all-zero watermarks and names the rejected v1 plan receipt.
The database has application ID 1127368498, user version 7, `integrity_check=ok`, and no foreign
key violation. The authority JSON binds every exact count and identity.

## Why a tool is required

A plain `mv` cannot prove ADR-0030's held-lock, no-follow inventory, Linux atomic no-replace,
directory durability, and post-transition byte-identity requirements. The repository has the
necessary low-level patterns but no operator command for this transition. The retired database
must also never be opened by corrected acquisition code. Therefore this review authorizes a
narrow independent module and CLI, with synthetic transaction tests, before any real mutation.

## Authorized files

Grok may create only:

- `src/cryptofactors/acquisition/binance_usdm_harmonic_gate2_retirement.py`;
- `scripts/research/retire_binance_usdm_harmonic_gate2.py`; and
- `tests/acquisition/test_binance_usdm_harmonic_gate2_retirement.py`.

The implementation must use only the Python standard library and must not import
`binance_usdm_harmonic_acquisition` or execute its CLI. Do not edit the accepted acquisition
source, acquisition test, acquisition CLI, authority JSON, governance, configuration, or data.

## Exact command contract

Expose `inspect` and `retire` subcommands. Production CLI operation derives the repository and
fixed `data/cex002_qualify` path from the exact authority; it must not accept an arbitrary store
or destination. `retire` must additionally require the exact rejected plan-receipt digest as an
explicit confirmation value. Both commands load the authority with no-follow regular-file
proof and require its exact byte SHA-256 above, closed schema, exact native JSON scalar types,
fixed paths, and exact execution-context source/test/CLI hashes. Test-only library injection
may supply a synthetic authority and digest; the production CLI pin must not be overrideable.

`inspect` is read-only. It acquires the existing `acquisition.lock` nonblocking and without
creation, holds it through all proof, then emits one bounded canonical JSON inspection result.
It must not create the retirement parent, open SQLite read-write, reconcile WAL, or alter any
tree entry.

`retire` performs the same complete proof under the same held lock, then exactly once:

1. open the repository, authority, store, active tree, lock, and every descendant through
   directory-relative no-follow descriptors; reject symlinks, special files, missing or extra
   entries, replacement races, device changes, and any mismatch with the ten-entry inventory;
2. stream-hash regular files with bounded memory, proving descriptor identity and stable
   metadata before and after each read;
3. parse the plan receipt and open `state.sqlite` only through its already-proved descriptor
   using SQLite `mode=ro&immutable=1` plus query-only behavior; prove the exact schema/table,
   authority, plan distribution, 90-retained, 202-gap, unfinished-run, zero-fact, ledger,
   seal-head, integrity, and foreign-key facts in the authority;
4. require the fixed retirement parent and fixed destination both absent, create only
   `gate2_retired` with mode 0700, and `fsync` its containing store directory;
5. open the parent no-follow, prove same device, then call Linux
   `renameat2(..., RENAME_NOREPLACE)` from `gate2` to the exact receipt-digest destination;
   there is no link/unlink, replace, copy, or cross-device fallback;
6. while still holding the moved lock descriptor, `fsync` both rename parents and call Linux
   `syncfs` on the containing filesystem; and
7. prove the active name absent, the retirement parent contains exactly the destination, the
   destination root retains the expected inode/device, and its complete post-tree inventory is
   byte-for-byte equal to the authority inventory.

On success emit one bounded canonical JSON receipt to stdout containing schema/ticket,
authority digest, rejected plan identities, source/destination, before/after inventory digest,
entry/byte counts, lock/no-replace/fsync/syncfs facts, and start/end timestamps. Do not print
manifest-sized or secret-bearing content.

Every pre-rename failure leaves the active tree untouched and returns a distinct nonzero safe
failure. Any failure after the rename returns a distinct indeterminate/durability failure,
reports whether source and destination exist, and performs no cleanup, reverse rename, retry,
or second transition. All descriptors unlock/close without masking the primary error.

## Required synthetic tests

The test source must construct small independent stores and cover at least:

- exact `inspect` success with no mutation and exact `retire` success preserving inode, mode,
  size, and hashes while removing only the active name;
- authority byte-hash/schema/type/path/context mismatch and arbitrary CLI target rejection;
- missing/extra/symlink/special/replaced/tree-device/inventory/hash/WAL mismatches;
- lock contention, pre-existing parent, pre-existing destination, and no-replace collision race;
- wrong application/user version, integrity/foreign-key failure, wrong/extra tables, receipt,
  authority, plan/retained/gap/run/fact/ledger/seal semantics;
- proof that SQLite is immutable read-only and the acquisition module is never imported;
- injected hash, `mkdir`, rename, parent-`fsync`, `syncfs`, and post-proof failures, including
  the no-cleanup distinction before versus after rename; and
- bounded streaming/no secret or manifest-sized output and exact receipt fields.

Tests may expose narrow injectable syscall/hash/clock hooks in the module; production defaults
must be the real safe primitives. Avoid duplicated production logic in tests.

## Stop boundary

Grok must not run commands/tests, use Git, touch the real store, or create execution evidence.
Return once with each authorized file's SHA-256 and line count plus the test-function count.

Integration, Ruff, pytest, control, real `inspect`, retirement, corrected planning,
acquisition, replay, `verify`, network access, later gates, and next-ticket work remain
unauthorized. After source/test acceptance, Hermes will integrate and validate the tool; real
retirement will require a separate exact execution authorization. Corrected planning will
remain a later separate review boundary. Gate 2 remains `IN_PROGRESS`; next ticket remains
`NONE`.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly this review, the authority JSON,
`docs/handoff/CURRENT_TASK.md`, and `tickets/CEX-002.md`. Developer source/test paths,
ignored state/data, and unrelated dirty work are excluded.
