# CEX-002 Grok Retained-Authority Complete Static Rejection

- **Date:** 2026-08-27
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** two-file drop rejected on complete static review; one consolidated correction authorized
- **Authorized actor:** Sr Dev - Grok Build, Grok 4.6 XHigh
- **Gate 2:** in progress; no raw acquisition fact exists
- **Next ticket:** `NONE`

## Reviewed drop

The reviewer inspected Grok's complete two-file return once without executing source, tests,
Ruff, control, planning, acquisition, or data commands:

| Path | SHA-256 | Lines |
|---|---|---:|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_acquisition.py` | `a26809ae0af30cf8a6b97ce9042763a486bb938a0fbc100a52bff50d2b894044` | 10,926 |
| `tests/acquisition/test_binance_usdm_harmonic_acquisition.py` | `210ef2107c38d4c3f13d02e1581c562d44aefe8597082be6fb9aee1ca81ea47e` | 5,390 |

The test source has 191 test functions. The unchanged CLI remains at SHA-256
`6f4b56ecb43dcc448eb6c8cf765e38d9fa3923432459574d913582e3d9c84043`. Only the two
authorized paths changed among CEX-002 source/test/CLI paths; unrelated dirty work remains
outside this review.

## Accepted direction

Preserve these parts of the drop:

- receipt 258 is decoded after its existing hash/size pin;
- one bounded `RetainedCredit` value carries the exact key set and compact decomposition;
- both plan-generation passes and `adopt_retained` consume that value rather than deriving a
  progress/plan intersection;
- unauthorized complete progress objects receive `retained: false`;
- planning proves receipt membership, unique digests, bytes, and selected/cost placement;
- the compact plan receipt omits the key list but binds its digest and decomposition; and
- the production-shaped test creates 90 complete progress/plan intersections, credits exactly
  73, downloads the other 17 normally, and proves the exact outcomes and network-call count.

These changes address the original runtime failure. Review 325 rejects integration because
the remaining authority and receipt defects are reachable and the review-324 contract was
explicitly fail closed at them.

## Findings

### 1. Receipt 258's retained-credit object is only partially authenticated

`authenticate_retained_credit_receipt` reads the keys, digest, primary counts, and bytes, but
does not require the exact retained-credit field set and ignores three accepted fields:
`rejected_recovered_rows`, `report_summary`, and `source`. It consequently accepts extra
fields and accepts a re-pinned receipt whose retained report summary contradicts the key,
object, byte, unverified, or rejected-row facts. It also does not re-prove lineage's explicit
`coefficient_only_keys_marked_retained == 0` fact. That is not the complete receipt contract
required by ADR-0030 and review 324.

The synthetic receipt fixture reproduces the partial object rather than the real accepted
shape, so no test can expose these omissions.

### 2. An incompatible plan-receipt shape reuses the v1 schema and policy identity

The drop adds a required top-level `retained_credit` field to the exact plan receipt while
leaving `PLAN_SCHEMA == cex002_gate2_plan_receipt_v1` and the ADR-0029 v1 policy identity.
Old and corrected receipts therefore claim the same exact schema/policy even though each is
invalid under the other's field contract. The corrected generation must be explicit v2
authority, not an incompatible reinterpretation of v1.

During receipt-chain authentication, the new compact retained block is checked only for field
names. Values are not type-checked, the digest need not be SHA-256, counts need not match
persisted pins, selected plus cost need not equal valid keys, and unverified need not be zero.
The receipt hash prevents unnoticed byte mutation, but it does not make internally
contradictory bytes valid under a declared schema. The exact v2 schema must authenticate its
own compact contract on every chain replay.

### 3. Required residual regression boundaries are absent or weak

The tests do not reject an extra/missing retained-credit field, altered report-summary or
rejected-row fact, nonzero coefficient-only lineage, schema/ticket mismatch, lineage-count
mismatch, nonzero unverified count, aliased retained digests, or invalid compact-plan receipt
values. The changed-authorized-set test permits either a changed semantic plan or merely a
changed receipt identity and never asserts that the semantic plan identity itself differs.
Review 324 required that exact proof because retirement/replanning depends on it.

The retained progress byte size also remains coerced through `int(...)`; an authority string
or boolean is not an exact positive integer even when coercion happens to equal the observed
size.

## Consolidated correction

Grok Build may continue editing exactly the same two files. Preserve all accepted direction
above and make one complete correction:

1. Define the exact receipt-258 retained-credit field set, including
   `rejected_recovered_rows`, `report_summary`, and `source`, and reject extra or missing
   fields. Define the exact report-summary field set and reconcile its five values with the
   primary retained block. Require exact nonnegative integers, a non-empty source string,
   rejected-row equality, and the accepted lineage key digest/count plus
   `coefficient_only_keys_marked_retained == 0`. Production constants may pin accepted scalar
   semantics, but the 73 full keys must still come only from receipt bytes.
2. Make retained progress `byte_size` an exact positive integer before equality and preserve
   all raw/sidecar/digest re-proof. Do not coerce strings or booleans.
3. Advance the corrected plan receipt to `cex002_gate2_plan_receipt_v2` and advance the policy
   identity to an explicit ADR-0029-plus-ADR-0030 v2 identity. Do not reinterpret v1. Run and
   terminal schemas need no field-shape change, but their policy reference must name the new
   policy.
4. Add one bounded validator for the compact v2 retained block and call it from receipt-chain
   authentication. Require exact fields/types, a lowercase SHA-256 digest, exact object/key and
   byte equality with persisted pins, selected plus cost equal valid keys, zero unverified,
   and the production 68/5 decomposition when the production receipt identity is in force.
5. Make the synthetic sizing receipt reproduce the complete accepted retained block and
   relevant lineage facts. Add bounded production-path tests for every omitted boundary listed
   in finding 3, including duplicate-content alias rejection and exact progress-byte typing.
6. Strengthen the changed-key-set test: compute both valid summaries without mutating installed
   state, assert different semantic plan identities and different compact provenance, then
   prove the second valid plan cannot attach to the first installed state.
7. Preserve every other source/test change and every accepted acquisition, concurrency,
   transaction, recovery, capacity, secret, provider, and receipt behavior. Do not add a
   migration, retirement command, compatibility mode, force/reset switch, or scope selector.

## Stop boundary

Do not run pytest, Ruff, control, planning, acquisition, verification, qualification, sizing,
capacity, network, data, or Git commands. Do not edit governance, the CLI, fixtures outside the
test file, or live/retired Gate-2 state. Return once with both hashes, both line counts, the
test-function count, and confirmation that only the two authorized paths changed.

Hermes integration/testing, old-store retirement, corrected real planning, acquisition,
replay, terminal verification, Gate 3, normalization, catalog, NautilusTrader, Harmonic
Trader, experiments, PAPER/LIVE, and next-ticket work remain unauthorized. Gate 2 remains
`IN_PROGRESS`; next ticket remains `NONE`.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly this review,
`docs/handoff/CURRENT_TASK.md`, and `tickets/CEX-002.md`. Developer source/test paths,
ignored state/data, and unrelated dirty work are excluded.
