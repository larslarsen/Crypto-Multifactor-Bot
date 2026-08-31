# CEX-002 Grok Revision-Candidate Source Static Rejection

- **Date:** 2026-08-31
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** source/test drop rejected before integration or execution
- **Authorized actor:** Sr Dev - Grok Build using Grok 4.6 High
- **Gate 2:** `IN_PROGRESS`
- **Next ticket:** `NONE`

## Drop identity and scope

The unintegrated Review-354 Grok drop stays within the four authorized path groups. Reviewer-
derived static identities are:

| Path | Lines | SHA-256 |
|---|---:|---|
| `src/cryptofactors/acquisition/binance_usdm_gate2_revision_candidate.py` | 2,307 | `dbb531f452519bc4262c6f437567d8ed2d6817c56d9d514995f1189d7ef87950` |
| `scripts/research/plan_binance_usdm_gate2_revision_candidate.py` | 98 | `4e3f85994a392340428b31a5c89d4bffd40229693bb5eb1fdbc39b87331f5331` |
| `tests/acquisition/test_binance_usdm_gate2_revision_candidate.py` | 1,260 / 29 test functions | `e8b9b476750e622f2069af43a6a3ed010a19199f6a980a6ee1035785a2b5b2d1` |
| `tests/acquisition/fixtures/binance_usdm_gate2_revision_candidate/listing_book_ticker_page.xml` | 16 | `37dfbef59851d00082db9b2c7d7788ee8b9c5000a5e084a3adbf7623766f158a` |
| `tests/acquisition/fixtures/binance_usdm_gate2_revision_candidate/listing_metrics_page.xml` | 16 | `d195b69931043014b904a68547dfeac8cb7237e8a8f5fc7c11f3b5704e6d75d0` |
| `tests/acquisition/fixtures/binance_usdm_gate2_revision_candidate/sidecar_btc_metrics.CHECKSUM` | 1 | `6dd7148990cd11f7b30e8de9bedd0fea88338c718ab20e3c1c58ee9238abbf55` |

No developer execution attestation was supplied. The reviewer ran no test, Ruff, compilation,
acceptance, planner, network, or raw-acquisition command. Static inspection and one intended
query-only SQLite fact read establish the findings below. Nothing in this review integrates or
accepts the drop.

## Accepted direction to preserve

The drop preserves the source-path boundary, does not edit the accepted acquisition engine,
pins the Review-354 counts and run-7 head, implements the ADR-0031 ZIP work equation correctly,
keeps pending-row iteration cursor-batched, rehashes retained sidecars, keeps candidate and
acquisition acceptance false, uses content addressing for page/manifest/receipt objects, and
provides a listing-only CLI without family/symbol/key/date or Coinalyze-secret controls. The
basic nonblocking lock, no-follow, checkpoint/resume, deterministic semantic-receipt, and
synthetic-test directions should be retained.

The drop is nevertheless rejected as one unit. The following are source-authority,
transaction, physical-read-only, and production-boundedness blockers.

## Finding 1 - the real pending facts cannot pass classification

The constants at production lines 98-105 omit the diagnostic type prefix. Actual latest
terminal facts contain these exact values:

```text
AcquisitionError: listed byte size does not match
AcquisitionError: stream exceeded the listed byte ceiling
AcquisitionError: streamed digest does not match the required checksum
AcquisitionError: ZIP uncompressed expansion exceeds the accepted ceiling
```

The accepted latest-pending split is respectively 12,576, 38,344, 1, and 354. Because
`_terminal_message()` returns the complete stored `error`, `_classify_pending_row()` rejects the
first real pending row before listing retrieval. The tests manufacture bare messages and thus
prove a different state contract.

Use the exact stored strings and require the exact four-way latest-attempt split, status 200,
class `terminal`, fact kind `validation`, exact official object URL, non-null end time, and
sealed attempt ownership. Test fixtures must use canonical production-shaped payload envelopes
and full diagnostics.

## Finding 2 - `mode=ro` is not physically read-only for this WAL database

`_open_sqlite_readonly()` uses `mode=ro` plus `query_only=ON`. On a WAL-mode database, that can
create or refresh `state.sqlite-shm`. The reviewer reproduced the side effect while confirming
Finding 1. This is a reviewer-procedure incident and an empirical proof that the proposed open
path violates ADR-0031's closed-generation rule even though no SQL row was written.

The connection is closed. No cleanup, deletion, checkpoint, or repair is authorized. Preserve
the current exact physical facts:

```text
state.sqlite
  bytes=2386247680
  sha256=5a5bdc8745c51b1b4b4a15e0de12b7dfa405f8c3a8ae1ba759aa0b6fd7ee33b4
  mtime=2026-08-31 12:10:08.070457829 -0700
state.sqlite-wal
  bytes=0
  sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
  mtime=2026-08-31 12:21:16.973277583 -0700
state.sqlite-shm
  bytes=32768
  sha256=fd4c9fda9cd3f9ae7c962b0ddf37232294d55580e1aa165aa06129b8549389eb
  mtime=2026-08-31 14:12:43.032969440 -0700
```

The correction must hash and bind the state file before SQLite open, require the WAL to remain
exactly empty, inventory any SHM/WAL leaves without modifying them, and use an actually
immutable held-descriptor SQLite open. Establish one explicit read snapshot after the
nonblocking acquisition lock and prove before/after state, WAL, and SHM identities unchanged.
A WAL-mode regression fixture must prove that the planner creates, deletes, truncates, or
changes no active-tree leaf or metadata. The existing SHM/WAL files are evidence to preserve,
not cleanup targets.

## Finding 3 - generation 0 is counted but not authenticated exactly

The source trusts a stored `seal_head.receipt_sha256` while omitting exact schema identity,
`pins_json`, authority-row cardinality, authority destination/device reconciliation, accepted
source/CLI file rehash, run-publication/run-seal/head cross-binding, watermark-to-table bounds,
and sealed semantic-prefix authentication. Equal-count row or schema substitution can pass.
Missing planner code files also become all-zero identities instead of blockers.

Logical closure is incomplete. It does not prove the authoritative per-family completion table,
the exact Coinalyze inventory/liquidation/gap partition, all 569 checksum-verified HTTP-200
charges, the 569/569/569 transition sequence, 20,126,995 charged bytes, 479,340 points, or the
ledger. Pending rows do not require database identity to equal envelope identity and payload
key, and the manifest omits the full old plan facts/ETag and exact attempt lineage.

Bind the exact state-file size/SHA above plus a canonical `sqlite_schema` identity. Rehash the
accepted generation-0 source and CLI through held repository descriptors and require:

```text
src/cryptofactors/acquisition/binance_usdm_harmonic_acquisition.py
  sha256=af6ef568b9f0f30827b393efc013b13560d4fd5761ec86417c0d2cf461e1248d
scripts/research/acquire_binance_usdm_harmonic_release.py
  sha256=6f4b56ecb43dcc448eb6c8cf765e38d9fa3923432459574d913582e3d9c84043
```

Then prove every Review-354 family/Coinalyze/charge/run predicate and exact canonical pending
envelope/URL/key/symbol/date/sidecar relationship. The candidate row must bind the complete old
plan payload identity and terminal-attempt lineage, not a hand-selected subset. A missing or
changed code path is a blocker; zero placeholders are forbidden.

## Finding 4 - roots are reopened instead of held

Although initial opens are no-follow, content, candidate, temporary, manifest, receipt, source,
capacity, and checkpoint operations later reopen pathname roots. `_write_manifest()` uses
`mkdir`, `open`, `read_bytes`, and `unlink` by path. A root or nested-directory swap can move
reads/writes away from the directory whose lock and device were proved. The current root proof
also accepts the store root, an ancestor, or an arbitrary same-device location as the candidate
root. Publication collision paths return `EEXIST` reuse without rehashing the winning leaf.

Hold generation, content, repository, candidate, page, temporary, manifest, and receipt
directory descriptors for the complete transaction. Perform every traversal, hash, capacity
measurement, cleanup, and publication relative to those descriptors; compare inode/device
facts after open; and rehash every collision winner. Production CLI layout must resolve to the
exact repository-bound `data/cex002_qualify/gate2` and sibling
`data/cex002_qualify/gate2_revision_candidate`; test injection may remain internal. Add root,
ancestor, rename/symlink-swap, nested-leaf, special-file, and collision-race test source.

## Finding 5 - listing/checkpoint facts are not request or version authority

The parser collects but discards echoed prefix, delimiter, and continuation token. The nested
metrics fixture actually echoes the family prefix for a child-prefix request, so the test
codifies a response/request mismatch. Root element, duplicate control elements, object-key
scope, sizes, ETags, response status, final URL, headers, and retrieval time are not bound.
`urllib` follows redirects, so an initial listing URL can cause a forbidden raw-object GET.

Checkpoint validation permits self-consistent orphan or foreign page records, forged completed
prefixes, arbitrary discovered prefixes, and a fake `listing_complete` state. Rebuild consumes
all checkpoint pages rather than the exact reachable request graph. Repeated continuation
tokens can loop forever. Duplicate-key checking is not a proof that relevant metadata stayed
stable across the listing generation.

Use an exact official-host, status-200, no-redirect listing response type. Strictly validate each
ListObjectsV2 response against its request, key scope, direct-child prefix grammar, entry/page
ceilings, and continuation progress. Checkpoint schema must bind the exact reachable pass graph,
generation/pending/code identities, request/response metadata, and content-addressed bytes;
reject every orphan, extra, missing, cyclic, or impossible state. Perform a second stable pass
or equivalent exact revalidation of every pending raw and sidecar listing fact and refuse drift.
Record retrieval clocks outside semantic identity. For each small checksum sidecar, bind current
listing size and single-part ETag to the retained bytes so the retained checksum is demonstrably
the current listed checksum version.

## Finding 6 - production listing and failure handling are not bounded/resumable

`_rebuild_listing_index()` materializes every object in both affected families in one Python
dictionary. Real nested listings contain far more than the 51,275 pending objects; the claimed
large test returns only pending flat objects and observes only SQLite cursor batches. It does
not exercise real family/symbol prefix traversal or irrelevant current objects.

Production has no resumable-partial transport path. Exit 2 is reachable only through the test
hook; DNS, timeout, connection, and interrupted response failures become blockers or uncaught
exceptions. Token/prefix/page/key counts and lengths have no global bounds.

Use a bounded on-disk candidate index or a streaming join so neither pending nor current listing
rows are one Python collection. Add exact page/prefix/token/key/byte ceilings and cycle checks.
Classify safe transient listing failures as durable resumable partials and format/authority
failures as blockers. Tests must use real nested prefix shape, include a large irrelevant listing
population, instrument both pending and listing live memory, and cover transient failure before
and after durable pages without a test-only interrupt being the only exit-2 mechanism.

## Finding 7 - publication is neither deterministic nor transactionally complete

The gzip writer inherits the randomized temporary filename into the gzip header because no
empty header filename is supplied. Thus compressed manifest identity can differ across clean
and resumed runs despite `mtime=0`. The manifest is read fully into memory and published to its
final directory before code identity, capacity, receipt, or commit-point publication succeeds.
A crash or later blocker can therefore leave public candidate rows with no receipt, contrary to
the function contract. Content collision winners are not always revalidated.

The semantic receipt commits only a digest/count of page identities; it discards the exact page
list, and the only reconstructing checkpoint is mutable. Rows do not bind their listing-page
lineage. No fixed no-replace locator commits exactly one candidate, and a completed checkpoint
can be reused after code/state/listing changes. Source/CLI hashes are measured only near the end,
so they need not identify the code that started the run.

Build manifest and an exact content-addressed listing-lineage manifest privately through held
descriptors. Use a fixed compression level, `mtime=0`, and an empty gzip header filename. Bind
each candidate row to old plan/attempt/sidecar facts and exact current listing lineage. Rehash
code at start/end, freeze the checkpoint identities, publish immutable assets, and use one fixed
no-replace locator as the commit point; a blocker or interruption before that point leaves no
public candidate row. Resume must recover the exact publication prefix or refuse it. Clean,
resumed, repeated, reordered, and publication-interrupted executions must produce byte-identical
manifest, lineage, semantic receipt, and locator identities.

## Test-source correction contract

In addition to direct regression coverage for every finding, replace bare terminal messages and
flat pseudo-production listing pages with exact accepted shapes. Add tests for:

- immutable WAL-mode query-only access with byte/metadata-identical active-tree inventory;
- exact state/schema/code/run/family/Coinalyze/charge and canonical pending-envelope binding;
- forged equal-count state, schema, head, watermark, plan payload, attempt, and charge facts;
- echoed-request mismatch, redirects, raw-object redirect, malformed/duplicate XML control
  fields, out-of-prefix keys, token cycles, orphan checkpoint pages, forged completion, and two-
  pass drift;
- retained sidecar/current listing size-and-ETag mismatch, including a checksum-version change;
- held-root and nested-directory substitution plus every no-replace collision winner;
- real nested production-shaped boundedness with irrelevant listing objects and bounded on-disk
  joins; and
- private-to-committed interruption at every publication boundary and byte-identical clean,
  resumed, and repeated output.

The large-count test must continue proving exactly 50,921 metrics plus 354 book rows without
materializing either the pending set or the enclosing current family listings as Python
collections.

## Correction authorization

Sr Dev - Grok Build using Grok 4.6 High is authorized for one consolidated correction in only:

- `src/cryptofactors/acquisition/binance_usdm_gate2_revision_candidate.py`;
- `scripts/research/plan_binance_usdm_gate2_revision_candidate.py`;
- `tests/acquisition/test_binance_usdm_gate2_revision_candidate.py`; and
- `tests/acquisition/fixtures/binance_usdm_gate2_revision_candidate/`.

Preserve the accepted direction, implement all seven finding groups and the test-source
contract as one coherent correction, and do not weaken ADR-0031. Grok must not run a command,
test, network/data operation, real SQLite open, planner, migration, acquisition, replay,
`verify`, integration, record edit, Git operation, or later-gate work. Do not inspect, remove,
rewrite, or otherwise touch the real `state.sqlite`, WAL, SHM, or any Gate-2 leaf. Stop for
reviewer static inspection with exact path SHA-256 values, line/test-function counts, and an
explicit confirmation that no command ran.

Hermes remains unauthorized. No source integration, candidate run, cleanup, state mutation,
generation transition, corrected acquisition, Gate 3, normalization, catalog, model, or next-
ticket work is authorized. Gate 2 remains `IN_PROGRESS`; next ticket remains `NONE`.

## Reviewer publication scope

Under the AGENTS reviewer-publication exception, the reviewer may stage, commit, and push
exactly:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/355_CEX002_GROK_REVISION_CANDIDATE_SOURCE_STATIC_REJECTION.md`; and
- `tickets/CEX-002.md`.

The unintegrated Grok source/test/fixture drop, real data/state, developer evidence, and all
unrelated dirty paths are excluded.
