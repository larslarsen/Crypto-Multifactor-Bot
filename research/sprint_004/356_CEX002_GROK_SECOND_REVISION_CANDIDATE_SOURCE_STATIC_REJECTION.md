# CEX-002 Grok Second Revision-Candidate Source Static Rejection

- **Date:** 2026-08-31
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** corrected source/test drop rejected before integration or execution
- **Reviewed actor:** Sr Dev - Grok Build using Grok 4.6 High
- **Authorized correction actor:** Sr Dev - Claude Build using Claude Opus 5
- **Gate 2:** `IN_PROGRESS`
- **Next ticket:** `NONE`

## Review boundary and drop identity

This is a static review of Grok's consolidated Review-355 correction. The reviewer did not run
the planner, tests, Python, Ruff, repository-control, an acceptance command, a network command,
or any SQLite/data command. In particular, the reviewer did not open, inspect, clean, repair,
or otherwise touch the real generation-0 `state.sqlite`, WAL, SHM, content tree, or candidate
tree. No developer execution attestation accompanied the drop.

The unintegrated drop remains confined to the four authorized path groups. Reviewer-derived
static identities are:

| Path | Lines | SHA-256 |
|---|---:|---|
| `src/cryptofactors/acquisition/binance_usdm_gate2_revision_candidate.py` | 3,050 | `20073f81d71b145e55bde9e47701b681d9e79a7aae5c383674d22dc5d2e28287` |
| `scripts/research/plan_binance_usdm_gate2_revision_candidate.py` | 87 | `9e203790432d412d489120fdef6bcb19831cf10461cecc38e7b1f23c41fb0d1a` |
| `tests/acquisition/test_binance_usdm_gate2_revision_candidate.py` | 1,321 / 22 test functions | `63cdada16a228898fb8b6dc496b5452850d3ac9c0ece95e683299c4835e988b3` |
| `tests/acquisition/fixtures/binance_usdm_gate2_revision_candidate/listing_book_ticker_page.xml` | 16 | `dd53323a7fcab0c39c8dd8d4824446fddc95b993c44671ead27144b064d84569` |
| `tests/acquisition/fixtures/binance_usdm_gate2_revision_candidate/listing_metrics_page.xml` | 16 | `d96c6713a29694264d5f3232bc04e085840b19d96d7f673e246ed36f473c5947` |
| `tests/acquisition/fixtures/binance_usdm_gate2_revision_candidate/sidecar_btc_metrics.CHECKSUM` | 1 | `6dd7148990cd11f7b30e8de9bedd0fea88338c718ab20e3c1c58ee9238abbf55` |

`HEAD == origin/main == 5a368401331284bc21496596ba095301f9367a35`. The source, CLI,
tests, and fixtures above are still untracked developer-drop files. Nothing in this review
integrates them.

## Material corrections accepted in direction

The correction is substantially better than the first drop. It now uses the four exact
`AcquisitionError: ...` terminal diagnostics and production counts, pins the accepted physical
SQLite leaves, opens SQLite through a held descriptor with `immutable=1` and `query_only=ON`,
rehashes accepted source/CLI files, validates much more of the schema/head/family state, holds
working directories for the transaction, refuses redirects in the production transport,
strictly checks important S3 response echoes and key scope, stores listing objects in a bounded
temporary SQLite index, classifies transient transport failures as resumable, uses deterministic
gzip metadata, and introduces an immutable locator commit point. The CLI has no caller-selected
economic filter. Those directions must be preserved.

The drop is nevertheless rejected as one unit. The remaining defects are authority and
transaction defects, not polish.

## Finding 1 - the claimed stable second pass is the first pass replayed locally

`_complete_listings()` fetches each request once, marks `listing_complete`, and then calls
`_rebuild_index_from_graph()` (production lines 2219-2299). The rebuild opens the same retained
page bytes from the first pass and compares their parsed objects to the index that those same
bytes populated (lines 2173-2216). It issues no independent second listing request and therefore
cannot observe a provider size, ETag, key, prefix, or pagination change. The error text
`listing drift across the stable second pass` describes an equality tautology, not a stability
proof.

This fails Review 355's explicit requirement for a second stable pass or equivalent exact live
revalidation of every pending raw and sidecar listing fact. The tests contain no two-pass
transport and no drift between independently retrieved passes. A listing can change immediately
after its only request and the candidate will still be published as current and stable.

Implement two independently retrieved, pass-identified reachable request graphs. Resume may
reuse a durable page only within its exact pass. Compare the final raw and sidecar facts for all
51,275 pending identities across passes and block any difference in presence, size, ETag,
request reachability, or relevant pagination authority.

## Finding 2 - response and checksum-version authority remain incomplete

The production transport compares only the final URL before `?` (lines 898-900), so a changed
prefix or continuation query is accepted. `_fetch_page()` independently trusts an injected
transport's final URL and body-length behavior (lines 2104-2133). The immutable lineage document
then drops the retained page record's `final_url` and `headers` (lines 2436-2456), and no retrieval
clock exists anywhere. Thus the receipt cannot reconstruct or authenticate the exact request,
response metadata, and nonsemantic retrieval evidence required by Review 355.

For current checksum authority, `_iter_manifest_lines()` verifies the sidecar's ETag only when
the listing happens to provide one (lines 2367-2378). A missing ETag passes. The correction must
require a present, syntactically single-part MD5 ETag for every checksum sidecar and bind it to
the retained bytes; absence, multipart syntax, or mismatch blocks. The current test covers a
wrong ETag only, not missing or multipart ETags or a checksum-version change across passes.

The XML parser also treats a missing or non-boolean `IsTruncated` as false (line 695) rather than
requiring one exact control value. Require exact response controls, exact final URL including
the canonical query, an independently enforced response-byte ceiling, canonical response
metadata in lineage, and retrieval clocks outside semantic identity.

## Finding 3 - checkpoint authority can still be forged or lost open

The checkpoint writes `generation_state_sha256` but `_authenticate_checkpoint()` never checks
it (lines 1829-1846 and 1998-2066). Authentication checks page-file hashes and that graph keys
match a page dictionary, but it does not derive the graph from the two roots and exact pagination
edges. It does not prove unique graph order, completed-prefix truth, cursor consistency, page
record fields, `published_pages`, family-prefix identity, or that `listing_complete` follows the
reachable graph. A self-consistent fabricated checkpoint and fabricated content-addressed pages
can therefore declare listing complete without network authority.

`_load_checkpoint()` catches every `UnsafeCandidateError` from opening the checkpoint and treats
it as absent (lines 1980-1985). A symlink, directory, special file, or other unsafe existing leaf
is silently handled like `ENOENT` and can be replaced. Its single capped `os.read()` also does
not prove an exact bounded file read. The completed-locator open repeats the broad fail-open
pattern at lines 2596-2599.

Runtime listing growth is not capped by `PAGE_COUNT_CEILING`; the page ceiling is checked only
when authenticating an already existing checkpoint. One prefix can therefore retrieve more
than the declared maximum before the next run refuses it. Continuation tokens are tracked in
one global list, so the same opaque token legitimately used by two different prefix chains is
misclassified as a cycle; membership also becomes linear. Bounds and cycle identity must be
enforced before each fetch/mutation and scoped to the exact request chain.

Replace permissive mapping checks with an exact checkpoint schema and typed fields, exact-size
reads, state/pending/code/pass binding, and reconstruction of every reachable root, child-prefix,
and pagination edge from authenticated page bytes. Distinguish absence from every unsafe open
failure. Reject extra, missing, duplicated, reordered, cyclic, impossible, or falsely completed
states. Add direct forged-state, forged-completion, malformed-type, unsafe-leaf, repeated-token-
across-prefixes, and live-ceiling test source.

## Finding 4 - generation and held-root proof still omit required exact predicates

The immutable connection is an important correction, but the planner never establishes the
explicit read transaction required by Review 355. It relies on a series of autocommit reads
rather than one explicit snapshot. The acquisition lock and immutable file reduce practical
drift risk; they do not satisfy the literal snapshot contract.

Pending-envelope validation still falls back to values derived from the key instead of
requiring stored `family` and `symbol` facts, does not require the canonical economic interval
or retained flag, and does not bind the recorded sidecar path to the held content-addressed leaf
(lines 1648-1742). Coinalyze validation proves aggregate transition status counts but not one
ordered `reserved -> published -> settled` chain for each of 569 exact charges, nor the complete
typed unsupported-gap partition (lines 1560-1629). The synthetic stores set charge and transition
counts to zero, so test source never exercises the accepted production charge chain.

Root handling remains pathname-based before the held descriptors exist. `_prove_candidate_layout()`
uses `Path.exists()`, `is_symlink()`, and `stat()`; `_plan_revision_candidate()` later opens the
repository, generation, and candidate roots independently and compares only candidate/generation
devices (lines 2459-2487 and 2544-2594). A same-device rename substitution between proof and open
is not bound through one held common parent or pre/post inode identity. The tests cover simple
inside/ancestor/symlink layouts, but not root or nested-directory substitution and not collision
races required by Review 355.

Use one explicit read transaction on the held immutable descriptor, require the exact canonical
pending payload/path relationships, prove charge transitions and typed gaps per identity, and
bind the exact sibling roots through a held common parent with device/inode facts after open.

## Finding 5 - completed-candidate recovery does not authenticate the candidate

When a locator exists, the early recovery path validates its schema string, code identity,
physical state hash, and receipt bytes only (lines 2596-2633). It does not open or rehash the
manifest or lineage, cross-bind their names and hashes to the receipt, validate the locator's
pending/semantic identities, or prove the receipt's current state/pending/code/manifest/lineage
relationships. It can return `EXIT_COMPLETE` and a manifest path when that manifest or lineage
is missing, substituted, truncated, or inconsistent. JSON and bounded-read failures on the
locator/receipt are also not converted to the required typed refusal, and the early return omits
the end-of-run code rehash.

The publication regression does not exercise the real commit boundary. Its
`interrupt_before_locator` hook fires before any immutable asset is published (lines 2807-2811),
not after the lineage, receipt, and manifest have been published and rehashed immediately before
the locator rename. There are no interruption hooks between those asset publications. Further,
the private manifest is copied with one `os.read(manifest_bytes)` and the published object's
digest is never required to equal the receipt's already computed `manifest_sha` (lines
2812-2820). A short read can therefore publish a different manifest while the receipt describes
the original.

Publish or stream the exact private manifest without a one-read assumption, cross-check every
asset against the receipt and locator, place the final pre-locator hook immediately before the
no-replace commit, and test every asset boundary. Locator recovery must authenticate the exact
locator schema, all three immutable assets, semantic identity, current generation/pending/code
identity, and final code hash before returning complete. Unreferenced content-addressed assets
may be reused only after exact reauthentication and must never be treated as a committed
candidate without the fixed locator.

## Test-source disposition

The 22-test correction covers several useful happy paths, but it does not implement Review
355's regression contract. Missing coverage includes independent two-pass drift; missing and
multipart sidecar ETags; exact final-URL query and raw-object redirect behavior; malformed or
missing XML controls; forged completion/state/type/edge checkpoints; live page/prefix/token
ceilings; root/nested substitution; every publication boundary; missing/tampered manifest and
lineage recovery; exact nonzero production-shaped charge transitions and gaps; and byte-identical
lineage/receipt/locator assets across clean, resumed, and reordered retrieval.

The production-shaped large test does exercise 50,921 plus 354 pending rows and an irrelevant
prefix through the on-disk index, which is worth preserving. Its memory hooks do not compensate
for the missing authority cases above.

## Correction authorization and routing

This is Grok Build's second rejected revision-candidate drop. Both misses concern the same
source-authority/transaction boundary. Under
`docs/engineering/DEVELOPMENT_ROLES.md`, repeated semantic misses should normally rotate to the
alternate formal senior. Sr Dev - Claude Build using Claude Opus 5 is therefore authorized for
one consolidated correction of only:

- `src/cryptofactors/acquisition/binance_usdm_gate2_revision_candidate.py`;
- `scripts/research/plan_binance_usdm_gate2_revision_candidate.py`, only if the corrected API
  requires a mechanical CLI adjustment;
- `tests/acquisition/test_binance_usdm_gate2_revision_candidate.py`; and
- `tests/acquisition/fixtures/binance_usdm_gate2_revision_candidate/` for bounded fixtures only.

Claude must preserve the accepted corrections, close all five findings and the missing test
contract as one coherent drop, and make no architecture or policy change outside ADR-0031 and
this review. It must not read, open, inspect, hash, delete, rewrite, or otherwise touch the real
generation-0 SQLite/WAL/SHM, content, or candidate data. It must not run the planner, a network or
data command, acquisition, migration, integration, repository-record edit, Git operation, or
acceptance command. The sole synthetic pytest exception below may exercise the planner only
inside pytest-managed temporary roots; it does not authorize the production CLI or layout.

After completing source and test-source edits, Claude is authorized under the targeted-senior-
test exception to run exactly one command, against synthetic temporary-rooted tests only:

```text
.venv/bin/python -m pytest tests/acquisition/test_binance_usdm_gate2_revision_candidate.py -q --tb=short
```

Claude stops on the first nonzero result. Whether zero or nonzero, it reports the exact command
and complete output, exact path SHA-256 values, line/test-function counts, and confirmation that
no other command ran. A zero result is immediate source feedback only; it is not integration,
evidence, or acceptance. Claude then stops for reviewer static inspection.

Hermes remains unauthorized. No source integration, candidate execution, cleanup, state
mutation, generation transition, corrected acquisition, later gate, model, or next-ticket work
is authorized. Gate 2 remains `IN_PROGRESS`; next ticket remains `NONE`.

## Reviewer publication scope

Under the AGENTS reviewer-publication exception, the reviewer may stage, commit, and push
exactly:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/356_CEX002_GROK_SECOND_REVISION_CANDIDATE_SOURCE_STATIC_REJECTION.md`;
  and
- `tickets/CEX-002.md`.

The unintegrated developer source/test/fixture drop, real data/state, developer evidence, and
all unrelated dirty paths are excluded.
