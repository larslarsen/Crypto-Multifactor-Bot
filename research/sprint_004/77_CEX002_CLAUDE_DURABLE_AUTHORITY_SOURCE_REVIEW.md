# CEX-002 Claude Durable Authority Source Review

Date: 2026-08-20

Reviewer: Lead Quantitative Finance Researcher/Engineer

Decision: **REJECT SOURCE DROP; ACCEPT CLOSED ITEMS; AUTHORIZE ONE FINAL BOUNDED
CLAUDE CORRECTION**

## Reviewed state

Committed base: `HEAD == origin/main == da43dd63a19123880d161bea22c5fcc5d8daa044`.

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `01ddd63d007162b1dcba6a76d164cdd70a3d344b88a96274669d7c0c780df1c5` |
| `scripts/research/qualify_binance_usdm_harmonic_sources.py` | `578f45e2be6f4428cc73560daacb31a305f72501f26f4ea2cd2c718a444fc64b` |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `0b9179173109f6f0c357d556ecf74e6990766b88487a0c2ae940ef648ef8130d` |
| `tests/acquisition/fixtures/binance_usdm_harmonic_qualification/exchange_info.json` | `9388b67710c51ce0a4219c2e23d57c804d01f4a54b08b340dff1e9bdbb414ed0` |
| `tests/acquisition/fixtures/binance_usdm_harmonic_qualification/coinalyze_future_markets.json` | `47416908780ef674efdf1cb3a62cb215c4f48834ad932f9c20e080eb6649b83f` |
| `tests/acquisition/fixtures/binance_usdm_harmonic_qualification/coinalyze_funding_rate_history_anchors.json` | `2537212f7b423a991a4ed9aa2413df72843dc059768e53f23260eddfe5de1f3f` |
| `tests/acquisition/fixtures/binance_usdm_harmonic_qualification/coinalyze_liquidation_history_anchors.json` | `d4e7834b6705e8c21329c04fa9738c29030e1da9c674b7d57e9ba4f3977e9ad0` |
| `tests/acquisition/fixtures/binance_usdm_harmonic_qualification/coinalyze_ohlcv_history_anchors.json` | `8fd1ddd5eb4b498badc4b203831872b3c1b006fb892f196f6d5273932d0de6d5` |
| `tests/acquisition/fixtures/binance_usdm_harmonic_qualification/coinalyze_open_interest_history_anchors.json` | `30be3ac8ba27213a381675f24a6f83b6de85d139032662101d14e9f8d626f9df` |

Only those nine CEX-002 paths were inspected. Every DEX/BitMEX path and transient
sidecar in the dirty worktree remains unrelated and excluded.

## Accepted closures

The write-ahead reservation now precedes acquisition, survives the exact checkpoint-to-
settlement interruption, and reconciles conservatively. Legacy spend is reported as a
zero-to-verified-total range. The public relock switch is gone; plan content, actions,
totals, URLs, keys, families, and normal-resume input stability are checked. Storage
credit now rehashes raw bytes and re-proves provider sidecars, while full-union,
confirmed-universe, and deduplicated physical totals are separately labelled.

The requested temporal cases now have typed blocking/nonblocking outcomes. Coinalyze
product gaps are no longer truncated. These directions and their tests must be preserved.

## Blocking findings

### 1. Current exchangeInfo authority is still separable from the retained response

`run_source_qualification` checks only that `raw_bytes` hash to the reported SHA and then
parses `exchange_response.payload`, not those raw bytes. A `CurrentContractSource` can
therefore return official retained bytes for one universe and a different parsed mapping
for classification in the same run. The structured response's endpoint, byte count,
retrieval time, and content path are also not checked against the official contract and
retained bytes before reliance.

`parse_exchange_info_rows` requires keys but not valid values. Empty `underlyingType`,
`pair`, status, base, quote, or margin values pass; invalid/null lifecycle values become
`None`; and a `PERPETUAL` row with an empty underlying type is confirmed because it is not
equal to `TRADIFI`. This is the same fail-open identity problem review 76 required closed.

Historical raw responses are now rehashed and reparsed, which is accepted. However,
mutable snapshot metadata still supplies `observed_at`, and that local value becomes an
exact close boundary for a closed-status contract. The authenticated response's
`serverTime`, not an editable local observation field, must supply any response-time
boundary.

### 2. The plan freezes claims rather than all re-proved authority inputs

Before the first lock, `retained_keys` accepts every completed checkpoint row's recorded
byte size without rehashing its raw object or re-proving its provider sidecar. The frozen
retained digest then hashes those checkpoint claims. A missing or tampered retained object
can therefore determine `reuse_retained` selection and become part of an allegedly
authoritative immutable plan before `_acquire_sample` discovers the failure.

The membership digest includes only a subset of each evidence record. Current
exchangeInfo evidence has no raw-response or complete canonical-row identity, and pair,
base, quote, margin, onboard, and delivery semantics are omitted. The inventory digest
contains parsed keys, sizes, and ETags but no stable manifest of the re-proved listing-page
request identities and raw response digests. This does not satisfy review 76's full
listing, membership, raw, and checksum evidence binding.

Freeze only currently rehashed/re-proved retained objects. Bind the plan to canonical
complete contract-row evidence and to a stable listing authority manifest consisting of
request identity plus retained raw-response SHA. Execution progress remains excluded so a
normal resume stays stable; any authority substitution must fail before sample download.

### 3. Persisted budget accounting accepts allowance-restoring values

`BudgetLedger.load` converts charge and reservation values to integers without requiring
strictly positive sizes, disjoint keys, or agreement between the stored and requested
budget. A valid-JSON negative charge or reservation reduces `charged_bytes` and restores
allowance. Durable accounting must treat such a ledger as an integrity failure, not as
spend.

Validate the complete ledger on load and before flush: positive bounded integer amounts,
disjoint charge/reservation keys, the expected budget identity, and consistent totals.
Add valid-JSON negative-value and budget-mismatch tests that prove failure before any
download.

### 4. Coinalyze validates native/provider identity only for anchors

The client verifies `symbol == coinalyze_perp_symbol(symbol_on_exchange)` while building
the two anchor rows, but the full support map marks every universe symbol present in
`markets_by_native` as supported without the same check. A non-anchor row with a correct
`symbol_on_exchange` and a mismatched provider symbol is therefore promoted into complete
coverage. Duplicate native identities also overwrite one another silently.

Validate the identity relation for every Binance perpetual market used by the support
map, reject duplicate native identities, and add focused non-anchor mismatch and duplicate
tests. Every unmapped symbol must remain retained as already implemented.

## Final bounded correction authorization

Sr Dev - Claude Build using Claude Opus 5 may modify only:

- `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py`; and
- `tests/acquisition/test_binance_usdm_harmonic_qualification.py`.

It must preserve every accepted review-76 closure and make only the four corrections
above. It performs no test execution, network/data run, integration, fixture or repository-
record edit, Git operation, commit, push, purchase, deletion, catalog mutation, Gate 2,
Nautilus, or Harmonic Trader work. It stops for fresh reviewer source inspection with the
two exact SHA-256 hashes. Hermes and every real rerun remain unauthorized.

## Publication set

Under the narrow reviewer governance exception, the reviewer may stage, commit, and push
exactly:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/77_CEX002_CLAUDE_DURABLE_AUTHORITY_SOURCE_REVIEW.md`; and
- `tickets/CEX-002.md`.

No source, test, fixture, data, prior record, or unrelated dirty path belongs to this
publication. The reviewer executes no tests or acceptance commands.

## Disposition

CEX-002 and Gate 1 remain `IN_PROGRESS`. Gate 2, Hermes integration, every real rerun,
Nautilus integration, every other ticket, and Harmonic Trader work remain unauthorized.
Next ticket remains `NONE`.
