# CEX-002 Typed Sizing Source Review

**Date:** 2026-08-23
**Reviewer:** Lead Quantitative Finance Researcher/Engineer
**Decision:** `REJECTED_ONE_BOUNDED_CORRECTION_AUTHORIZED`
**Architecture:** ADR-0017 and ADR-0021 as amended by ADR-0024
**Gate 1:** Accepted
**Gate 2:** Blocked; acquisition is not authorized

## Reviewed drop

Claude edited exactly the three review-230 paths and stopped without integration, evidence
publication, or Git work. The unintegrated identities are:

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py` | `d33d2cce90fa0b4f8b16736916a00f5bac1a8b0f1a3d18b37cea49f564e10003` |
| `tests/acquisition/test_binance_usdm_harmonic_sizing.py` | `91adc68309a728436d9c57bee09bd8a3aae10e4b13932a0007893174a97c24ec` |
| `scripts/research/size_binance_usdm_harmonic_release.py` | `36740c926c32e4973bb31dcb570d3c69b89f9f343d52eb8aed3d33d359d7b23c` |

The test file has 101 `def test_` functions. Static whitespace inspection passes. The
reviewer did not execute source, tests, Ruff, sizing, or data commands.

The drop correctly introduces the fixed v2 receipt and evidence namespaces, keeps v1
targets separate, measures Parquet payload/footer/framing separately, groups projected
bytes by symbol/month, removes the full second normalized allocation, retains accepted
authority and identity checks, and keeps the six-component capacity equation explicit.
Those parts must be preserved. The drop is nevertheless rejected before Hermes because
four source contracts remain materially wrong.

## Blocking findings

### 1. Numeric conversion silently changes source values

`KIND_NUMERIC` is `pa.float64()` and `convert_numeric` returns Python `float`. This rounds
valid decimal lexemes while the source and test claim conversion never rounds. Testing
only `1.5` hides the defect. Prices, quantities, volumes, notionals, rates, ratios,
percentages, and liquidation values must use an exact fixed decimal representation with a
pinned precision/scale policy. Conversion must parse from the original token, prove exact
representability, and block rather than round or overflow.

Coinalyze remains the v1 string envelope: `point_token` stores a complete JSON object per
row, repeats string identity metadata, and projects a whole-file ratio. It is absent from
the typed schema contract. Its `t`, `l`, and `s` fields must be parsed directly from the
retained JSON lexemes into exact timestamp/long/short typed columns, with provider/native
identity and compact lineage represented once under the same v2 payload/overhead rules.
JSON parsing must preserve numeric lexemes rather than first converting them through
binary float.

### 2. Archive packages are mislabeled as required products

The 16 declared `LOGICAL_OUTPUTS` are daily/monthly physical-package variants, not the
ticket's required products. Daily and monthly packaging is split into different product
names even though it is one non-overlapping normalized product. Premium-index klines are
incorrectly labeled `*_taker_flow`; ADR-0021 assigns their two contributions to indicative
funding and basis. The declared trade-flow schema contains only taker-buy values and omits
the total base/quote volumes needed to derive taker-sell flow and imbalance.

The schema contract never represents `binance_usdm_funding_indicative_1h`,
`binance_usdm_mark_index_basis_1h`, `binance_usdm_perpetual_membership`, the typed
per-product coverage/gap product, or `binance_usdm_harmonic_bundle`. It also leaves the
observed-liquidation product outside the contract as an untyped string envelope.

Replace package-named outputs with explicit required-product schemas and separately named
physical-family contributions. Daily/monthly objects must feed one product partition set.
Multi-family products may conservatively sum independently measured typed contributions
per product/symbol/month, but the receipt must identify the final required product,
component, field/type/nullability contract, final file count, and byte equation. Count
membership, typed gaps, and the final bundle through explicit fixed schemas and byte
bounds, not only unnamed 4,096-byte catalog pages. All required product names are fixed by
the ticket; changing them requires an ADR and is not authorized here.

### 3. Real lineage is replaced by fabricated metadata

The real Binance checkpoint uses `retrieval_time`; the new source reads `retrieved_at`, so
every real retained sample falls back to the invented string `checkpoint_complete`.
Unknown retrieval time is thereby fabricated rather than retained as unknown. The
`source_availability` column is populated from checkpoint status `complete`, although the
accepted report's actual field is `availability_semantics`, such as
`source_object_listing_time_unknown`.

Build an exact key-indexed binding between the accepted report sample records and the
re-proved checkpoint. Preserve `retrieval_time` exactly when known and explicit unknown
when not; preserve the report's availability semantics and nullable
`source_available_at` separately from checkpoint completion state. Reject missing,
duplicate, conflicting, or substituted bindings.

The implementation also describes `raw_object_ref` as partition-local but measures one
96-row global manifest and charges it once per physical object. A raw object feeding two
products needs a mapping in each applicable product partition under ADR-0024's
partition-local design. Measure and project manifest payload/overhead per actual
product/symbol/month mapping, including repeated cross-product references, or stop for an
ADR amendment before choosing a release-global reference scheme. Do not silently combine
the two designs.

### 4. The five-minute metrics cadence has no calendar ceiling

`calendar_row_bound` discovers cadence only from a path segment such as `1h`. Binance
daily metrics keys contain no interval segment, so `daily/metrics` falls back to the
observed row-to-compressed-byte ratio even though the accepted product is fixed five-minute
OI/metrics. Pin the accepted 300-second family cadence, apply the daily/monthly calendar
maximum as applicable, and publish which exact bound won for every product contribution.
Unknown fixed cadence must block; it must not silently become event-driven.

## Authorized correction

Sr Dev - Claude Build on Claude Opus 5 is authorized to correct only:

1. `src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py`;
2. `tests/acquisition/test_binance_usdm_harmonic_sizing.py`; and
3. `scripts/research/size_binance_usdm_harmonic_release.py` only if the corrected source
   contract changes its already-v2 output text or imports.

Preserve all accepted v1 authority, retained credit, provider/native identity, secret
redaction, raw/cost scope, deterministic publication, v2 namespace, payload/overhead
separation, per-partition ceiling arithmetic, one-allocation capacity equation, and
content-addressed reuse logic.

Add or correct tests that prove:

- adversarial decimal lexemes survive exact typed conversion byte-for-byte in value and
  reject precision/scale overflow without echoing the token;
- retained Coinalyze `t/l/s` points are typed, exact, separately named, and never stored as
  JSON point strings;
- the required ticket product names and schemas are complete, daily/monthly packaging
  feeds one product, premium contributes to indicative funding/basis, and trade flow
  retains total and taker-buy inputs needed for sell/imbalance;
- membership, product gaps, observed liquidation, and the bundle have explicit schemas
  and independently recomputable storage bounds;
- real-shaped checkpoint `retrieval_time` and report `availability_semantics` are retained,
  unknown availability/retrieval is not invented, and binding damage blocks;
- partition-manifest mappings and overhead are counted for each actual product partition
  and source contribution; and
- daily metrics uses the fixed 300-second calendar ceiling even though its archive key has
  no interval segment.

Tests must not encode the rejected packaging-product names, float64 numeric policy,
`point_token` schema, fabricated lineage fallback, global-manifest accounting, or
observed-only metrics row bound as expected behavior.

Claude runs no test, Ruff, sizing, network, data/evidence mutation, record edit, Git,
commit, push, acquisition, normalization, catalog publication, or later command. Stop
after this one correction for reviewer inspection with the three exact SHA-256 hashes and
test-function count.

This reviewer-authored publication is restricted to exactly:

1. `research/sprint_004/232_CEX002_TYPED_SIZING_SOURCE_REVIEW.md`;
2. `docs/handoff/CURRENT_TASK.md`; and
3. `tickets/CEX-002.md`.

## Stop boundary

The reviewed source drop is not accepted or authorized for integration. This authorizes
one correction of the four consolidated findings only. It authorizes no command execution,
evidence publication, receipt 231, Gate-2 acceptance, acquisition, reduced universe,
reduced product set, reduced cost sample, paid data, Harmonic Trader, payoff analysis,
PAPER, LIVE, or next-ticket work. Next ticket remains `NONE`.
