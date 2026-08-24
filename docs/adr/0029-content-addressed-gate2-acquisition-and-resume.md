# ADR 0029 - Content-Addressed Gate 2 Acquisition and Deterministic Resume

- **Status:** Accepted
- **Date:** 2026-08-23
- **Amends:** ADR-0017 acquisition execution and ADR-0028 gate boundary
- **Evidence:** `research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json`,
  `research/sprint_004/258_CEX002_GATE2_STORAGE_SIZING_V3.json`,
  `research/sprint_004/282_CEX002_GATE2_CAPACITY_ATTESTATION.json`, and
  `research/sprint_004/283_CEX002_CAPACITY_ATTESTATION_INTEGRATION_AND_EXECUTION.md`

## Context

Gate 1 and the accepted v3 sizing basis have fixed the complete raw requirement. It is
not a price-only release and it is not tick or historical order-book acquisition. The
official Binance portion contains 733,203 selected history objects from ten bar,
metrics, and funding families plus 3,144 first/midpoint/last cost-calibration objects
from daily `bookTicker` and `bookDepth`. Those sets are disjoint and total 736,347
objects and 20,356,940,843 listed bytes. Seventy-three already-retained objects provide
5,225,416 bytes of separately re-proved credit, leaving 20,351,715,427 projected new
Binance bytes.

The accepted secondary-source scope is one retained Coinalyze future-market inventory
and 569 Binance-native to provider mappings for daily observed/censored liquidation
history through the accepted qualification cutoff. The 202 unsupported accepted
memberships remain typed gaps. Bounded retained BTC/ETH liquidation, OI, funding, and
OHLCV responses qualify and size the source; they do not turn two anchor symbols into the
release universe. The accepted new Coinalyze raw allocation is 30,580,702 bytes.

Attestation 282 proves the fixed 139,577,980,018-byte stable requirement plus its current
57,891,047,015-byte reserve fits the destination. Its state is `sufficient`, with
91,986,203,943 bytes of headroom at publication. It is measurement evidence, not raw
acquisition or Gate-2 acceptance.

The remaining execution must survive interruption across roughly 1.47 million official
object and checksum requests without rewriting a giant JSON checkpoint on every object,
holding large responses in memory, duplicating completed coverage, or allowing a mutable
provider inventory to change the frozen universe.

## Decision

### 1. Frozen economic and authority scope

Gate 2 consumes only these accepted authorities:

1. report 62 at SHA-256
   `f27b2ba7e6eff3a8b1385d985c49ee64ef60a394737b1246130d0f37b9015f09`;
2. the compressed manifest detail at SHA-256
   `64d0f74b8e4696c98d0f96423185fd961aba6c63348d12425e3ec364b888f113`,
   with uncompressed SHA-256
   `d6c1fac650aaf16d88750da2a40d837f543d0c5fc88c73d463753a576d5bdd17`;
3. complete cost-manifest identity
   `04842ff6b9b58280b3ec2ea2644b3d44769be62d460bef785262cd4dd65cac57`;
4. sizing receipt 258 at SHA-256
   `3995a5072a7d84baecae677ceff6e1c7af9dd076daadec04a31717ffc8f16589`;
5. sufficient capacity attestation 282 at SHA-256
   `0e12333d94b7ce2aea373c7f4bac7887a5f72c6a710cb9e697c5ffb660c22b25`;
6. the listing checkpoint, official contract metadata, version-4 lock, amendment ledger,
   qualification progress, qualification source, and qualification CLI identities bound
   by receipt 258; and
7. prospective holdout boundary
   `c842f813839e1dda375b351da0f693c54bcf932e33eb6e3394aba860c12346e2`.

Every identity and all visible counts, byte equations, membership sets, mapping sets,
cutoffs, families, and retained-credit facts are re-proved before a plan is installed.
The complete manifest is exposed only after `iter_manifest_detail` has fully validated
it. Any live helper module whose semantics are used is hash-authenticated first and its
identity is included in the plan receipt.

No caller-selected family, symbol, date, cadence, endpoint, or product filter exists.
The plan includes no `trades`, `aggTrades`, full historical `bookTicker`, or full
historical `bookDepth`. The two book families contain only the accepted 3,144-object
cost sample.

### 2. Immutable logical plan

The planner produces one canonical plan identity without duplicating the 466 MB
uncompressed manifest as another authoritative file. Its ordered records are:

- the 736,347 exact Binance object keys, families, Binance-native symbols, listed bytes,
  economic intervals, sidecar keys, and retained states; and
- 570 Coinalyze logical receipts: the accepted retained inventory and one full accepted
  lifecycle daily liquidation request for each of the 569 frozen mappings.

Coinalyze mapping pairs are reconstructed only from the rehashed retained
`/future-markets` response using its `symbol` and `symbol_on_exchange` fields, then
intersected with the exact 569 supported Binance-native identities. Current provider
inventory never expands, shrinks, or remaps the plan. Request bounds come from accepted
official lifecycle evidence and the fixed report cutoff, not current time. The retained
BTC/ETH multi-symbol response remains qualified evidence and reusable point lineage, but
it cannot falsely mark either full-lifecycle one-symbol request complete.

The plan receipt binds the ordered plan digest, all authority and code identities,
counts, bytes, family totals, retained decomposition, Coinalyze mappings and request
rules, holdout, storage destination/device, and prohibitions. Planning performs no
network call. Replanning the same authority against an empty state produces the same
semantic plan identity; a different authority cannot attach to an existing state store.

### 3. Durable progress state

One SQLite database beneath the accepted store root is the operational progress store.
It uses a fixed schema and application/user versions, foreign keys, WAL mode,
`synchronous=FULL`, explicit transactions, and a single-process no-follow lock. Its
tables separate immutable authority, plan entries, append-only attempts, immutable
completion facts, run metadata, and terminal gaps. The logical primary key is provider
plus exact plan request/object identity.

`complete` is monotone. A completed identity cannot be replaced, reset, or revised in
place. A different provider checksum, content hash, listed size, response revision, or
request identity is a typed revision conflict. The operator cannot force, skip, unlock,
delete, or relock it through the CLI.

An interruption may leave an unreferenced immutable blob or private partial file, but it
cannot create a completion row before durable content exists. On resume:

1. completed rows re-prove their exact content and sidecar paths before reuse;
2. a durably recorded sidecar may locate and adopt an already-published raw content blob
   after full revalidation; and
3. incomplete private partials are removed or ignored and never treated as coverage.

Completed coverage performs zero network requests on replay. Concurrent workers may
download, but one coordinator owns database writes and terminal state transitions.

### 4. Immutable raw publication

All new raw responses and Binance checksum sidecars are streamed to private files on the
destination device, hashed while streaming, flushed and fsynced, and published without
replacement under a SHA-256 content address sharded by the first digest byte. The parent
directory is fsynced before the completion transaction. Existing content is rehashed
before reuse. Symlinks, non-regular files, path traversal, cross-device publication, and
content-address collisions fail closed.

For every Binance object, Gate 2:

1. fetches and retains the exact listed `.CHECKSUM` sidecar;
2. proves the sidecar names the selected object basename unambiguously and parses one
   SHA-256;
3. streams the selected ZIP with its exact positive listed-size ceiling;
4. requires the listed byte size and provider SHA-256 to match;
5. checks the ZIP central directory, member safety, non-empty file membership, and CRC
   without extracting to a release tree; and
6. records safe HTTP revision headers, retrieval time, content path, sidecar path, and
   validation state.

Deep economic parsing and normalized-product quality remain Gate 3. Gate 2 never labels a
checksum-valid raw object as economically valid merely because the ZIP opens.

### 5. Bounded scheduling, retry, and interruption

The engine uses a pooled streaming transport with a fixed reviewed worker ceiling and
bounded queue. It never buffers an object or response in memory. It has deterministic
bounded retry classes and backoff; honors a bounded `Retry-After` for 429 responses; and
does not retry terminal authentication, request-shape, checksum, size, or revision
failures. Every attempt has a redacted durable fact.

The CLI exposes `--max-objects` and `--max-wall-seconds` only as operational stop bounds.
They cannot select economic scope or promote a partial run. When the bound or signal is
reached, scheduling stops, in-flight transactions settle, a run receipt is published,
and the process exits with an explicit resumable state. An abrupt kill leaves the same
state recoverable on the next invocation.

### 6. Coinalyze boundary

The API key is read only from `COINALYZE_API_KEY` and sent only in the `api_key` header.
It never enters a URL, query identity, database, receipt, log, exception, or test artifact.
The plan uses `/liquidation-history`, interval `daily`, one provider symbol per logical
request, `convert_to_usd=false`, and the fixed lifecycle/cutoff. This stays within the
official 20-symbol request maximum and uses the accepted conservative one-symbol request
shape. A shared limiter enforces no more than 40 provider-symbol calls per minute and
honors `Retry-After`.

Responses are content-addressed and parsed with exact decimal lexemes. The returned
provider symbol must exactly match the request; timestamps must be unique, ascending,
daily, and inside the fixed bounds; `l` and `s` must be finite non-negative decimals.
Empty or provider-unavailable histories are retained where a response exists and become
typed source outcomes, never invented zero liquidation. An identity mismatch,
malformed response, secret leak, or cumulative new Coinalyze raw bytes above the accepted
30,580,702-byte allocation blocks without publishing the offending response as complete.

The three retained OI/funding/OHLCV responses stay bounded Gate-4 reconciliation evidence.
Gate 2 does not expand them into full-history acquisition.

### 7. Capacity guard

Before planning publication, every acquisition run, and any individual transfer whose
listed ceiling could cross the guard, the engine revalidates attestation 282 and
recomputes the ADR-0028 reserve from current same-device available bytes. The complete
accepted 139,577,980,018-byte stable requirement remains charged throughout Gate 2; no
mutable progress credit reduces it. This intentionally double-counts already-acquired
new raw during Gate 2 and is conservative. If the full stable basis plus current reserve
does not fit, scheduling stops before another network transfer.

The engine cannot create a new capacity attestation or override the stable basis,
reserve, device, or state. A later normalization authorization may require a fresh
attestation after Gate-2 evidence is accepted.

### 8. Receipts and Gate-2 completion

Every bounded invocation publishes an immutable content-addressed run receipt containing
the plan/code identities, start/end times, stop reason, exact attempt/completion/gap
deltas, byte deltas, pre/post capacity facts, and a deterministic semantic state digest.
It contains no full object list and no secrets. Mutable SQLite bytes are never treated as
the evidence identity.

The offline verifier rehashes every completed content and sidecar, reconciles the full
plan and all state counts, and publishes a canonical compressed terminal acquisition
manifest plus a compact terminal receipt. Gate 2 can be accepted only when:

- every one of the 736,347 Binance plan objects is checksum-verified or has an explicit
  reviewer-disposed terminal source outcome;
- all 570 Coinalyze logical receipts and all 202 unsupported mappings reconcile without
  identity drift or silent omission;
- no request remains planned, in flight, retryable, ambiguous, or over budget;
- a second network-enabled replay performs zero downloads and creates no new completion;
  and
- the terminal receipt and manifest reconcile raw logical identities, unique content
  hashes, physical bytes, attempts, typed outcomes, and retained/new decomposition.

A complete run with unresolved required official objects remains blocked. Partial
progress is `IN_PROGRESS`, never PASS.

## Consequences

- Gate 2 can run in bounded resumable sessions without loading the manifest or large raw
  objects into memory.
- SQLite provides efficient operational state; immutable run and terminal receipts
  provide reviewable evidence independent of SQLite file bytes.
- No paid data, tick history, full historical book, live stream, normalization, model,
  NautilusTrader, Harmonic Trader, PAPER, or LIVE work is authorized by this ADR.
- The storage precondition is accepted, but Gate 2 itself remains incomplete until real
  acquisition, replay, and terminal verification evidence are reviewed.
