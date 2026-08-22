# CEX-002 Real Authority Decomposition Review

**Date:** 2026-08-22
**Reviewer:** Lead Quantitative Finance Researcher/Engineer
**Decision:** `REVIEWER_INFERENCE_CORRECTED_ADR0023_SOURCE_CORRECTION_REQUIRED`
**Architecture:** ADR-0023 amends ADR-0021 and ADR-0022
**Gate 1:** Accepted
**Gate 2:** Not accepted

## Review-220 correction result

Claude returned sizing production SHA-256
`e4ff6c12789d4e9d23814477f4268eaf05c23f4e4e32ceb8492ef06b30b56971` and test SHA-256
`3c19c5f081b09aa42985faeb4c44f3c418eb515acfc346cacdec6033ce38ed6a` with 58 test
functions. Static inspection confirmed all four review-220 corrections. The complete
focused suite then had one failure: the newly required report-summary preflight correctly
blocked an older hypothetical duplicate test whose synthetic report had not been changed
with its monkeypatched authority. The reviewer made only that mechanical fixture update;
the current test SHA-256 is
`617c0fc5cbfa43e817e8c8a107756643ec50e9ede3d72a9ed91012f11882bbc2`.

After that fixture correction, all 122 focused cases passed in 3.1 seconds, exact-path
Ruff passed, and restricted whitespace validation passed. The sizing CLI remains unchanged
at SHA-256 `78ee687c734fc94070952d290752acdbd007970fb26c616e5e6845f1de3702ad`.

## Early real-store failure

The reviewer then ran a read-only real-store authority and retained-credit probe through
the uncommitted corrected source. It loaded the pinned report/lock/ledger/source/checkpoint/
listing/metadata authority, streamed and rehashed the 733,203-row manifest detail, resolved
all 3,144 cost objects from rehashed listing evidence, and entered retained proof. It wrote
no byte and invoked no network.

The probe failed closed before sizing-envelope or receipt publication:

```text
accepted sizing authority does not match its pinned identity
field=cost_retained_keys actual=5 expected=17
```

This is not a cache, source, checkpoint, or report failure. It exposes a reviewer inference
error in reviews 217, 219, and 220 and the narrative of record 218. The accepted report
states 56 selected-manifest consumable rows and 73 valid Gate-2 retained requirement keys;
it does not state that the remaining 17 are cost keys.

## Exact corrected decomposition

The reviewer performed a second read-only structured intersection over the exact pinned
report, manifest, checkpoint, and rejected lineage set:

| Set | Count |
|---|---:|
| selected requirement keys | 733,203 |
| complete-cost requirement keys | 3,144 |
| checkpoint rows | 440 |
| rejected ambiguous recovered rows | 176 |
| effective checkpoint rows | 264 |
| selected manifest rows marked consumable | 56 |
| effective selected requirement keys | 68 |
| effective complete-cost requirement keys | 5 |
| effective selected-plus-cost requirement keys | 73 |

There is no consumable row outside the effective authority. The 12 selected effective keys
not marked manifest-consumable are six daily metrics objects and six monthly funding-rate
objects. The five cost keys are one `bookDepth` and four `bookTicker` objects, including
the two basename-unique recovered `bookTicker` rows already accepted by ADR-0022.

The report's pinned Gate-2 credit was computed by the qualification source's shared
`retained_credit_decomposition()` over the complete requirement and effective checkpoint.
It reports 73 valid keys, 73 unique objects, 5,225,416 bytes, and zero unverified objects.
Those totals and the resulting 20,351,715,427 projected new Binance raw bytes remain exact.

ADR-0023 accepts the corrected authority distinction. Gate 1 remains accepted; no
qualification rerun or data mutation is needed.

## Claude correction authority

Sr Dev - Claude Build is authorized to edit only:

1. `src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py`; and
2. `tests/acquisition/test_binance_usdm_harmonic_sizing.py`.

Preserve every accepted review-219/220 correction and the reviewer's current duplicate-
fixture update. Make this one complete ADR-0023 correction:

1. Rename the selected credit concept from `selected_consumable_keys` to
   `selected_retained_keys`. Pin it to 68 and pin `cost_retained_keys` to 5.
2. Add a separate accepted manifest-consumable count of 56. Derive it while streaming the
   pinned manifest, reject any mismatch, and publish it separately in the receipt.
3. For Gate-2 credit, consider every effective checkpoint row whose full key belongs to
   the selected-plus-cost requirement. Do not require a selected row's manifest
   `consumable` flag. Continue to exclude report-declared rejected lineage, apply the
   independent recovered-basename binding rule, and rehash object, sidecar, and declared
   size before any key earns credit.
4. Classify each surviving logical key by actual membership in the selected or cost
   requirement set. Prove 68 selected plus 5 cost equals 73 total valid keys, 73 unique
   digests, and 5,225,416 unique bytes. Preserve deduplication by digest.
5. Make comments, returned fields, receipt fields, constants, and tests use the exact
   authority names. Nothing may describe the manifest's 56 consumable rows as the selected
   Gate-2 credit set or infer cost count through subtraction.

Update the synthetic fixture so at least one valid selected checkpoint key is deliberately
not marked manifest-consumable and still earns selected retained credit after full reproof.
Preserve the ambiguous recovered Kline rejection, fresh exact colliding key acceptance,
basename-unique recovered `bookTicker`, duplicate-digest, evidence-damage, report-summary,
receipt, no-network, mutation-boundary, and all prior sizing tests. Add explicit assertions
for 56 manifest-consumable, 68 selected retained, 5 cost retained, 73 total keys, 73 objects,
and 5,225,416 bytes.

Claude runs no pytest, Ruff, control, real-store probe, sizing, qualification, network,
data mutation, Git, commit, push, record, or control operation. Return both exact SHA-256
hashes and the test-function count, then stop. The reviewer will rerun focused validation
and the read-only real-store probe before any integration.

## Stop boundary

Hermes and sizing execution remain unauthorized. No bulk acquisition, normalization,
catalog publication, NautilusTrader, Harmonic Trader, payoff analysis, PAPER, LIVE, paid
source, reduced scope, or next-ticket work is authorized. Gate 2 remains unaccepted and
next ticket remains `NONE`.
