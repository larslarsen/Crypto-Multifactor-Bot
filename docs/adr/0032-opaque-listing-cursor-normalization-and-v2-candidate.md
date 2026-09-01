# ADR 0032 - Opaque Listing-Cursor Normalization and V2 Revision Candidate

- **Status:** Accepted
- **Date:** 2026-09-01
- **Amends:** ADR-0031 revision-candidate listing stability, semantic identity, and blocked-candidate preservation
- **Evidence:** `research/sprint_004/385_CEX002_DUPLICATE_INVOCATION_AND_DRIFT_BLOCKER_RECORD.md`

## Context

The ADR-0031 v1 planner completed two independent listings of both fixed Binance family prefixes.
Each pass reached the same 1,308 prefixes and 2,093 request pages, and every pending raw/sidecar
fact was retained. Candidate publication nevertheless blocked before manifest creation because
the implementation required the two `_stable_pass_graph` documents to be byte-equal.

The first difference is graph index 319. Both passes have the same initial request key and exact
request for `data/futures/um/daily/metrics/1000000MOGUSDT/`, the same empty child-prefix list, and
the same `is_truncated=true` fact. Only `next_continuation_token` differs. Binance S3 continuation
tokens are opaque cursors. A different token can identify the next page of the same ordered
listing and is not an economic key, object fact, reachability fact, or stable provider version.

The v1 comparison also includes token-bearing request keys in each pending object's cross-pass
fact. Even if the graph check ignored the next token, equivalent pending objects reached through
different opaque cursors would fail. The v1 manifest and receipt semantic identity likewise bind
pass-2 request keys/page hashes through physical lineage. That evidence must remain exact, but its
transport cursor cannot define the candidate's economic semantic identity.

The blocked v1 candidate is valuable immutable evidence. Its checkpoint binds the v1 source hash,
so corrected source cannot honestly resume it as though the new code created those pages. It must
not be deleted, rewritten, relabeled, or silently adopted by a new code identity.

## Decision

### 1. Preserve v1; create an independent v2 candidate

The complete-but-blocked tree at
`data/cex002_qualify/gate2_revision_candidate` remains immutable evidence under its v1 checkpoint
and source identity. Corrected code uses the absent fixed sibling
`data/cex002_qualify/gate2_revision_candidate_v2`.

V2 uses distinct candidate, checkpoint, lineage, and locator schema identifiers ending in `_v2`,
sets `ADR_ID` to `0032`, and uses a v2 policy identity naming ADR-0032. It does not import, copy,
hard-link, rename, mutate, or authenticate v1 as v2. Its listings start from an empty v2
checkpoint, so all v2 request/response lineage is produced under the v2 code identity.

### 2. Separate semantic reachability from transport cursors

Each pass still must independently and completely traverse both fixed family roots. The
cross-pass stable-reachability graph is canonicalized by prefix and zero-based page ordinal within
that prefix. Each normalized page contains only:

- the exact prefix;
- page ordinal within that prefix;
- sorted child prefixes; and
- the exact truncated/non-truncated flag.

Both passes must have the same roots, completed/discovered prefix sets, per-prefix page counts,
child-prefix reachability, and truncation sequence. Endpoint, delimiter, list type, prefix bounds,
token-cycle detection, ceilings, retained-page authentication, and complete checkpoint invariants
remain mandatory within each pass.

The following remain exact physical lineage but are excluded from cross-pass semantic equality:

- request continuation token;
- next continuation token;
- token-derived request key;
- final URL;
- response content hash and headers; and
- retrieval timestamp.

This exclusion does not permit missing, repeated, cyclic, cross-prefix, or unauthenticated pages.
It only prevents an opaque provider cursor from masquerading as an economic or reachability fact.

### 3. Compare pending object facts without page locators

For each pending identity and checksum sidecar, the two passes must agree on the object key, exact
listed size, and ETag. The sidecar ETag remains subject to the accepted single-part validation.
Token-derived request keys and response-page hashes are excluded from cross-pass equality and the
stable pending-facts digest. Exact pass-specific request/page identities remain in lineage and in
the physical manifest row selected from pass 2.

Any key absence, size drift, ETag drift, reachability drift, page-count drift, child-prefix drift,
or truncation-sequence drift still blocks.

### 4. Split semantic row identity from physical evidence identity

The v2 manifest remains a canonical compressed JSONL evidence asset containing exact pass-2
request/page lineage. The receipt adds a `semantic_rows_sha256` over canonical row projections
that retain all economic, generation-0, classification, checksum, size, terminal-attempt, and ZIP
policy facts while excluding only pass-specific transport locators:

- `current_listing.request_key` and `current_listing.page_sha256`;
- `current_sidecar_listing.request_key` and `current_sidecar_listing.page_sha256`; and
- `listing_page_lineage`.

The receipt semantic payload binds manifest format, row count, and `semantic_rows_sha256`, but not
the compressed/uncompressed physical manifest hashes, physical name, or physical byte count. The
locator and ordinary receipt envelope continue to bind the exact physical manifest, receipt,
lineage asset, and all content-addressed pages.

The normalized stable-graph and pending-facts digests remain in the semantic receipt. Therefore
two fresh stable v2 candidates with equivalent provider facts but different opaque cursors,
request keys, response hashes, headers, URLs, or retrieval clocks have the same semantic identity
while retaining distinct exact physical evidence.

### 5. Scope and completion remain unchanged

V2 remains listing-only. It cannot GET a raw ZIP, use Coinalyze, edit generation 0, select a
family/symbol/key/date subset, authorize acquisition, transition generations, or pass Gate 2.
The exact 50,921 metrics-revision plus 354 book-ticker ZIP-work pending scope and every ADR-0031
ZIP/capacity requirement remain unchanged.

## Consequences

- Opaque provider cursor rotation no longer produces a false reachability-drift blocker.
- Real prefix, pagination-shape, object-size, or ETag drift still fails closed.
- Physical evidence retains every cursor and response identity for audit.
- Semantic identity describes economic/provider facts rather than transport-session artifacts.
- The v1 blocked candidate remains available for audit, while v2 incurs a fresh listing-only run
  under its own code and schema authority.
- No raw acquisition or later gate is authorized by this ADR.
