# CEX-002 Storage Architecture Correction

**Date:** 2026-08-23
**Reviewer:** Lead Quantitative Finance Researcher/Engineer
**Decision:** `RECORD229_ACCEPTED_V2_SIZING_SOURCE_AUTHORIZED`
**Architecture:** ADR-0017 and ADR-0021 as amended by ADR-0024
**Gate 1:** Accepted
**Gate 2:** Blocked; acquisition is not authorized

## Single review outcome

Hermes's record 229 and commit
`2f60d5913f361c82b6960faa582d71845366b5e6` are accepted as the complete version-1
storage-sizing execution. The commit contains exactly the six authorized paths, is
published at `origin/main`, and passes commit whitespace validation. The accepted
production/test/CLI identities remained exact. Focused pytest passed 181 cases, exact-path
Ruff passed, and the two local sizing invocations produced byte-identical receipt and
evidence-store manifests. No network, acquisition, normalization, catalog publication, or
later work occurred.

Receipt 180 is accepted at SHA-256
`f2e1fef8156e3af1abd40554e5a8393ee6566e1719cf990a2a49867e5aef185c` as valid blocked
measurement evidence. It proves:

| Component | Bytes |
|---|---:|
| new Binance raw | 20,351,715,427 |
| new Coinalyze raw | 29,072,901 |
| normalized/catalog v1 bound | 188,932,621,323 |
| duplicate-stage temporary high water | 191,116,312,315 |
| operating reserve | 31,711,886,541 |
| total v1 requirement | 432,141,608,507 |
| post-publication available | 158,559,266,533 |
| shortfall | 273,582,341,974 |

The projected new raw allocation is therefore 20,380,788,328 bytes, or 20.381 decimal GB
/ 18.981 binary GiB. Including the 6,715,875 retained Binance and Coinalyze bytes already
on disk, the complete raw footprint is 20,387,504,203 bytes. There is no hidden raw trade
tape, historical order book, Tardis purchase, or terabyte-scale source requirement.

## Root cause and decision

The v1 bound is honest under ADR-0021 but is not an efficient release architecture.
Daily book ticker alone is projected at 112,793,591,029 normalized bytes because a generic
row-preserving envelope repeats long string metadata and applies the 3,058/317 whole-file
ratio from a tiny one-row witness to 11,692,468,351 family bytes. Daily metrics adds
60,465,126,261 bytes by the same mechanism. The current publisher assumption then adds a
second complete 188.93 GB normalized/catalog allocation.

Removing only the duplicate stage would still require 241,025,296,192 bytes, exceeding
available capacity by 82,466,029,659 bytes. Buying storage, shrinking the universe,
discarding derivative inputs, or reducing the cost sample is rejected. ADR-0024 instead
requires typed product-real sizing plus partition-atomic publication. It retains all
3,144 selected cost objects and every required economic row and field; exact source tokens
remain in immutable raw bytes with partition-level lineage.

Receipt 180 and its 98 ignored v1 envelopes remain immutable evidence. Gate 2 remains
blocked, and no acquisition is authorized until a reviewed v2 receipt proves capacity.

## Authorized senior source drop

Sr Dev - Claude Build on Claude Opus 5 is authorized to implement ADR-0024 in exactly:

1. `src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py`;
2. `tests/acquisition/test_binance_usdm_harmonic_sizing.py`; and
3. `scripts/research/size_binance_usdm_harmonic_release.py`.

Preserve every accepted authority, retained-credit, identity-namespace, secret-redaction,
raw-byte, Coinalyze, reserve, deterministic-serialization, and idempotence invariant. Do
not alter qualification source, report 62, manifest detail, locks, ledgers, checkpoints,
raw evidence, receipt 180, or the existing v1 envelopes.

The production source must:

- publish only schema `cex002_gate2_storage_sizing_v2` to the fixed new receipt path
  `research/sprint_004/231_CEX002_GATE2_STORAGE_SIZING_V2.json` and a distinct v2 envelope
  root, never rewriting v1 evidence;
- define and serialize the complete fixed logical-output schemas, types, nullability,
  dictionary/provenance representation, writer identity, and physical-family mapping;
- parse every retained sample row and write target-real typed envelopes for each logical
  output, including all book-ticker and book-depth rows/fields and all required metrics;
- fail closed on parse, integer, finite-number, range, nullability, schema, semantic, or
  lineage errors without echoing credentials or untrusted values;
- separate typed data-page/column-chunk bytes from footer, row-group metadata, and fixed
  framing, and project exact product/symbol/UTC-month groups using ADR-0024 integer-ceiling
  rules rather than one family-wide whole-file ratio;
- publish every ratio witness, sample/row/row-group count, partition grouping, payload,
  footer/metadata, framing, logical-output multiplicity, largest partition, and sum so the
  reviewer can recompute the receipt without trusting prose;
- keep the exact 20,351,715,427 Binance and 29,072,901 Coinalyze new-raw authorities and
  independently reconcile all family, partition, membership, gap, and catalog counts;
- calculate temporary high water without a full second normalized/catalog allocation,
  using the greatest explicit ADR-0024 bounded work unit, then recompute the exact capacity
  sum and blocked/sufficient state against post-publication availability; and
- make an identical rerun strictly verify/reuse v2 envelopes and reproduce stable receipt
  bytes while permitting only declared filesystem observations to vary under the existing
  rerun contract.

The tests must preserve all 181 accepted cases and add focused coverage for each new typed
schema and logical mapping; strict type/conversion failures; no cost-row/field/sample
reduction; compact manifest lineage; tiny-file footer non-amplification; per-partition
grouping; row-group overhead; integer ceilings; exact capacity arithmetic; no duplicate
normalized allocation; v1 immutability; v2 content-addressed reuse/collision refusal;
secret redaction; deterministic receipt bytes; and blocked/sufficient boundary values.

Claude may refactor the three authorized paths enough to remove superseded v1 sizing logic,
but must keep the accepted authority proof intact and must not weaken a test to obtain a
smaller number. Claude performs no test, Ruff, sizing, network, data/evidence mutation,
record edit, Git operation, commit, push, acquisition, normalization, catalog publication,
or later work. Stop once for reviewer inspection with exact SHA-256 hashes and the test
function count.

This reviewer-authored publication is restricted to exactly:

1. `docs/adr/0024-typed-normalization-and-partition-atomic-publication.md`;
2. `research/sprint_004/230_CEX002_STORAGE_ARCHITECTURE_CORRECTION.md`;
3. `docs/handoff/CURRENT_TASK.md`; and
4. `tickets/CEX-002.md`.

## Stop boundary

This authorizes one senior source/test/CLI implementation drop and one reviewer inspection.
It authorizes no integration, command execution by Claude, network, sizing run, deletion,
Gate-2 acceptance, acquisition, normalization, catalog work, NautilusTrader, Harmonic
Trader, payoff analysis, PAPER, LIVE, paid data, reduced universe, reduced product set, or
reduced cost sample. Next ticket remains `NONE`.
