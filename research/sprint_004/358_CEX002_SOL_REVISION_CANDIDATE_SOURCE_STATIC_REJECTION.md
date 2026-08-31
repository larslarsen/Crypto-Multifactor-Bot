# CEX-002 Sol Revision-Candidate Source Static Rejection

- **Date:** 2026-08-31
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** rejected before integration
- **Reviewed actor:** Sr Dev - Codex Sol using GPT-5.6-sol High
- **Authorized corrective actor:** Sr Dev - Codex Sol using GPT-5.6-sol High
- **Gate 2:** `IN_PROGRESS`
- **Next ticket:** `NONE`

## Reviewed drop and command result

The reviewer statically inspected Sol's Review-357 drop at these exact identities:

- production: 4,299 lines, SHA-256
  `48f3288774bef9f631ad962b61149bb1982743786545216771d55b66acdbfa60`;
- CLI, unchanged: 87 lines, SHA-256
  `9e203790432d412d489120fdef6bcb19831cf10461cecc38e7b1f23c41fb0d1a`;
- test source: 2,121 lines and 45 test functions, SHA-256
  `290b5a29385a698695de57c38fab6ada6ca25b8b0f26689c78de8212e632acf0`;
- book-ticker fixture, unchanged: SHA-256
  `dd53323a7fcab0c39c8dd8d4824446fddc95b993c44671ead27144b064d84569`;
- metrics fixture, unchanged: SHA-256
  `d96c6713a29694264d5f3232bc04e085840b19d96d7f673e246ed36f473c5947`;
- checksum fixture, unchanged: SHA-256
  `6dd7148990cd11f7b30e8de9bedd0fea88338c718ab20e3c1c58ee9238abbf55`.

Sol ran the one Review-357 command exactly once:

```text
.venv/bin/python -m pytest tests/acquisition/test_binance_usdm_gate2_revision_candidate.py -q --tb=short
```

It stopped correctly on the nonzero result: 70 of 74 parameterized cases passed and four
failed. All four failures are test-construction defects. The drift and sidecar-ETag tests put
BTC and ETH object identities in the BTC child-prefix response, so the newly strict scope check
correctly returns `listing object is outside the requested prefix` before the intended drift or
ETag assertion. The complete failure output is retained in the actor's Review-357 handoff.

Sol attests that it edited only the production and test paths, ran no other executable, test,
network, data, planner/CLI, acquisition, migration, acceptance, or Git command, and did not touch
the archive or real generation-0 state/WAL/SHM/content/candidate data. The reviewer executed no
test, Python, planner, SQLite, network, or data command during this review.

## Material corrections preserved

The drop materially closes Review 356's principal defects. It now performs two genuinely
independent listing passes, binds exact final request URLs and canonical response headers,
requires a single-part checksum-sidecar ETag, reconstructs checkpoint graph reachability,
enforces live page and traversal counts, holds descriptor-rooted directories, uses an explicit
SQLite transaction and exact pending/charge predicates, authenticates completed manifest and
lineage assets, streams deterministic manifest/gzip publication, and tests a production-shaped
50,921-metrics/354-book/569-charge case. Those corrections must be preserved.

## Blocking findings

### 1. Completed recovery does not authenticate all receipt claims

The completed-candidate path authenticates locator and asset hashes, checkpoint/listing
lineage, manifest rows, totals, and pending digest. It does not independently recompute and
compare all semantic receipt claims derived from those facts. In particular, metrics/book byte
splits and deltas, classification counts, provider-revision and ZIP-expansion counts, maximum
object bytes, and capacity-projection equations/booleans/statements can be changed in a newly
canonical receipt and locator and still be accepted. The content-addressed hashes establish
self-consistency, not truth, because no prior candidate hash is pinned.

Recovery must recompute every deterministic receipt claim from authenticated manifest/current
facts and reject any mismatch. Capacity claims whose free-space observation is historical must
be internally recomputed from the receipt's authenticated inputs rather than compared with
today's free space. Add a test that forges a canonical false receipt, republishes its matching
content-addressed leaf and locator, and proves recovery rejects it.

### 2. The final locator commit remains exposed to nested-directory and state/code races

At the last pre-commit hook the source rebinds the store, Gate-2, content, and candidate roots,
but not every held nested publication directory (`tmp`, listing pages, manifests, receipts, and
lineage). A same-device replacement of one nested directory can therefore make the committed
locator refer to missing or substituted assets. Code hashing and the SQLite leaf snapshot also
occur before that hook. A post-snapshot code or state replacement can publish the locator first;
the later SQLite check can only report the already-public inconsistency, and code mutation is not
rechecked at all.

Immediately after the final injectable/race boundary and before the locator rename, rebind every
held root and nested directory, rehash the code identity through its held authority, and
reauthenticate the SQLite database/WAL/SHM leaves. No failure may leave a committed locator.
Tests must exercise replacement of each nested directory plus code and SQLite mutation at that
boundary. Preserve the after-commit checks as defense in depth.

### 3. Physical leaf snapshots do not bind the opened descriptor to the named stat

The leaf-snapshot helper stats a name and separately opens/hashes it, but does not compare the
opened descriptor's `fstat` device, inode, mode, size, and modification identity with the named
leaf before and after hashing. A concurrent rename can mix facts from different objects.

Bind the held descriptor to the exact named pre/post stat identity and fail closed on any
difference. Add a deterministic swap test at this boundary.

### 4. Checkpoint and lineage byte ceilings are not enforced before durable writes

Checkpoint JSON is serialized and replaced without proving it is at most the declared
checkpoint ceiling. Lineage is fully materialized without enforcing its declared ceiling.
Allowed page/header counts can therefore create a durable checkpoint that the bounded resume
reader cannot reopen, or an unbounded lineage body before publication.

Enforce the serialized-byte ceilings before every durable checkpoint mutation and before
lineage publication. The failure must be deterministic and must not publish a locator. Add
focused lowered-ceiling tests for both artifacts.

### 5. Named publication does not fail closed on an unsafe existing winner

The named page/lineage publication helper handles absence but can leak an uncaught `OSError`
when the intended content-addressed destination is a symlink, directory, device, or other unsafe
leaf. That is neither the planner's stable blocked result nor safe winner authentication.

Use the same no-follow regular-file collision discipline as descriptor-backed publication,
mapping unsafe leaves to the exact planner failure surface. Add symlink and non-regular collision
tests and prove no locator is committed.

### 6. Pending rows are not bound to a canonical family/symbol/date key grammar

Pending classification checks the supplied family and compares the payload symbol with a helper
derived from the key, but it does not prove that the key belongs to that family, has a nonempty
canonical symbol, and encodes the exact payload symbol/date. A relabeled or malformed identity
can therefore pass the semantic predicate when the surrounding facts are self-consistent.

Define and enforce one exact metrics/bookTicker pending-key grammar. Bind family, symbol, date,
raw key, sidecar key where applicable, and payload fields bidirectionally. Add family, symbol,
and date mismatch tests.

### 7. The SQLite transaction/schema proof needs exact boundary closure

`BEGIN` is deferred until the first read, while the injectable hook occurs before that read. The
source must establish the immutable read snapshot before the hook. Schema comparison also must
reject unexpected schema-object types such as views or triggers, not merely extra named tables
or indexes. Add focused tests for both predicates.

### 8. The four failed test cases require scoped fixture construction

Each synthetic child-prefix response must contain only objects under that exact requested
prefix. Correct the two-pass drift and checksum-sidecar ETag tests without weakening the strict
scope check or changing their intended assertions.

## Bounded Sol correction authorization

Sr Dev - Codex Sol using GPT-5.6-sol High remains the sole authorized senior actor. It must make
one consolidated correction for the eight findings above while preserving every material
Review-356 correction already present. Its writable scope remains exactly:

- `src/cryptofactors/acquisition/binance_usdm_gate2_revision_candidate.py`;
- `scripts/research/plan_binance_usdm_gate2_revision_candidate.py`, only if mechanically required
  by the corrected API;
- `tests/acquisition/test_binance_usdm_gate2_revision_candidate.py`; and
- `tests/acquisition/fixtures/binance_usdm_gate2_revision_candidate/` for bounded fixtures only.

Sol may use read-only static inspection commands for the active ticket, governing documents,
and authorized source/test paths. It may not inspect or touch the real generation-0 SQLite,
WAL, SHM, content, candidate data, or `~/cmb_archive/`. It performs no network/data operation,
standalone planner/CLI, acquisition, migration, integration, repository-record edit, Git
operation, commit, push, or acceptance command.

After editing, Sol may run exactly one new targeted command against synthetic pytest-managed
temporary roots:

```text
.venv/bin/python -m pytest tests/acquisition/test_binance_usdm_gate2_revision_candidate.py -q --tb=short
```

Sol stops on the first nonzero result. Whether zero or nonzero, it reports the exact command and
complete output, exact SHA-256 and line count for every edited path, the test-function and
collected-case counts, and confirmation that no other executable/test/network/data/Git command
ran. The result is source feedback only and does not integrate or accept the drop.

Hermes remains unauthorized. No candidate execution, cleanup, state transition, corrected
acquisition, Gate 3, model, or next-ticket work is authorized. Gate 2 remains `IN_PROGRESS` and
next ticket remains `NONE`.

## Reviewer publication scope

Under the AGENTS reviewer-publication exception, the reviewer may stage, commit, and push
exactly:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/358_CEX002_SOL_REVISION_CANDIDATE_SOURCE_STATIC_REJECTION.md`; and
- `tickets/CEX-002.md`.

Developer source/test/fixture paths, real state/data, implementation evidence, and every
unrelated dirty path are excluded.
