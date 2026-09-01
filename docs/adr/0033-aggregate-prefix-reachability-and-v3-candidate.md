# ADR 0033 - Aggregate Prefix Reachability and V3 Revision Candidate

- **Status:** Accepted
- **Date:** 2026-09-01
- **Amends:** ADR-0032 cross-pass listing stability, semantic identity, and blocked-candidate preservation
- **Evidence:** `research/sprint_004/396_CEX002_V2_DRIFT_DIAGNOSIS_AND_PUBLICATION_EVIDENCE_COMPLETION.md`

## Context

The ADR-0032 v2 planner completed two independently authenticated traversals of both fixed Binance
family roots. Both passes reached the same 1,308 discovered and completed prefixes and ended with
null cursors. Pass 1 used 2,093 pages; pass 2 used 2,094 pages.

The first normalized difference is `data/futures/um/daily/metrics/BANKUSDT/`. Pass 1's single
terminal page ended with the 2026-08-30 ZIP and checksum. Before pass 2 reached that prefix,
Binance published the 2026-08-31 ZIP and checksum. Those two unrelated leaf objects crossed the
1,000-object boundary, so pass 2's first page became truncated and a second terminal page was
required. The new objects are outside the frozen generation-0 pending set. Both traversals are
complete, their prefix reachability is identical, and the exact pending objects can still be
compared by key, size, and ETag.

ADR-0032 correctly treated page count and truncation sequence as semantic reachability facts and
therefore blocked. The evidence now shows that this rule confuses a live provider's physical page
partition with the authority needed for the already frozen pending revision. Repeating two long
serial traversals while daily objects are published can fail indefinitely even when every relevant
pending object and every reachable prefix is stable.

The complete-but-blocked v1 and v2 trees remain valuable evidence bound to their respective source
and schema identities. Neither may be rewritten or resumed under corrected semantics.

## Decision

### 1. Preserve v1 and v2; create an independent v3 candidate

The blocked trees at `data/cex002_qualify/gate2_revision_candidate` and
`data/cex002_qualify/gate2_revision_candidate_v2` remain immutable evidence. Corrected code uses
only the absent fixed sibling `data/cex002_qualify/gate2_revision_candidate_v3`.

V3 uses distinct candidate, checkpoint, lineage, and locator schema identifiers ending in `_v3`,
sets `ADR_ID` to `0033`, and uses the exact policy identity
`adr0033_aggregate_prefix_reachability_and_v3_candidate_v3`. It does not import, copy, hard-link,
rename, mutate, or authenticate either earlier candidate as v3. Every v3 listing page is obtained
under the v3 code identity from a fresh empty v3 checkpoint.

### 2. Keep complete authenticated pagination mandatory within each pass

Each pass must independently traverse both exact fixed family roots to a null cursor. Existing
endpoint, list-type, delimiter, prefix-bound, response-authentication, request-echo, retained-page,
checkpoint, token-cycle, object-count, byte, prefix-count, page-count, and recovery checks remain
mandatory.

Within a pass, every truncated page must have one valid next ListObjectsV2 continuation token and
the chain must continue; every terminal page must be non-truncated without a next token. Page
ordinal, page count, truncation flag, current and next tokens, request key, response hash and bytes,
headers, final URL, retrieval time, child prefixes, and listed objects remain exact physical
lineage. This ADR relaxes no single-pass completeness or authentication rule.

### 3. Compare aggregate prefix reachability across passes

After both passes are complete and authenticated, v3 constructs one canonical reachability
document per pass containing:

- the exact sorted root set;
- the exact sorted discovered-prefix set;
- the exact sorted completed-prefix set; and
- for every discovered/completed prefix, the exact prefix plus the sorted set union of all child
  prefixes returned across every authenticated page for that prefix.

The two canonical documents must be byte-equal. Consequently any root, discovered/completed
prefix, or aggregate child-prefix drift still blocks.

Page boundaries do not define aggregate prefix reachability. The following remain exact physical
evidence but are excluded from cross-pass reachability equality:

- per-prefix and total page counts;
- page ordinal and truncation sequence;
- current and next continuation tokens and token-derived request keys; and
- response bytes/hashes/headers, final URLs, retrieval clocks, and the placement of an unrelated
  leaf object on a particular page.

Thus an unrelated leaf-object insertion or removal may change physical page partitioning without
blocking, provided both passes are complete, the aggregate prefix namespace is unchanged, and all
frozen pending-object facts satisfy the separate exact comparison below.

### 4. Keep frozen pending-object authority exact

For every frozen generation-0 pending identity and checksum sidecar, both passes must contain and
agree on the exact object key, listed size, and ETag. The accepted single-part sidecar ETag rule
remains mandatory. Any relevant key absence, size drift, ETag drift, pending-count drift, or
pending-identity drift blocks regardless of aggregate prefix equality.

Only leaf objects outside the frozen pending set are excluded from cross-pass semantic equality.
This ADR does not allow a missing or changed pending raw object or checksum sidecar to be hidden by
stable prefix reachability.

### 5. Separate stable semantic identity from physical page shape

V3 replaces the v2 stable-page-graph digest with `stable_reachability_sha256`, computed over the
canonical aggregate reachability document. The receipt and lineage claims bind that digest and the
existing exact stable pending-facts count and digest.

The ordinary receipt and locator continue to bind exact content-addressed manifest, receipt,
lineage, and page assets. The physical receipt and lineage retain exact per-pass page counts and
every page's pagination metadata. Manifest rows retain their exact selected pass-2 page locators.

The v3 `semantic_sha256` projection excludes total/per-pass page counts and all physical
pagination shape from both listing and lineage claims. It retains the v3 schema/policy/code and
generation identities, family roots/pass identities, `stable_reachability_sha256`, exact stable
pending-facts digest/count, semantic manifest-row digest, classification, byte/capacity facts, ZIP
policy, and no-authorization state. The existing semantic manifest-row projection continues to
exclude pass-specific request/page locators and listing-page lineage.

Two fresh candidates produced by the same v3 code with identical aggregate reachability and
pending economic/provider facts therefore have the same semantic identity even if unrelated live
objects cause different page counts or truncation sequences. Their exact physical receipts,
lineage assets, and page evidence remain distinguishable and fully authenticated.

### 6. Scope and authority remain unchanged

V3 remains listing-only and measurement-only. It cannot GET a raw ZIP, use Coinalyze, edit
generation 0, change the frozen pending set, select a subset, authorize acquisition, transition
generations, accept the candidate, or pass Gate 2. Every ADR-0031 ZIP/capacity rule and every
unrelated safety invariant remain unchanged.

## Consequences

- Daily leaf-object publication within an existing prefix no longer creates a false semantic
  blocker solely by moving the provider's 1,000-object page boundary.
- Real prefix reachability drift and every relevant pending-object absence or mutation still fail
  closed.
- Each pass must still prove a complete, bounded, authenticated traversal, and all differing page
  shapes remain durable physical evidence.
- Candidate semantic identity binds the frozen revision authority rather than incidental transport
  partitioning.
- V1 and v2 remain immutable audit evidence; v3 incurs a new listing-only traversal under its own
  code and schema authority.
- No acquisition or later gate is authorized by this ADR.
