# CEX-002 Review 476 - Price-State Acceptance and Liquidation Source Authorization

- **Date:** 2026-09-08
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** accept both Batch A products; authorize the bounded Batch B source drop
- **Gate 2:** `ACCEPTED`
- **Gate 3:** `IN_PROGRESS` - seven of eleven required products accepted
- **Next required actor:** Sr Dev - Codex Sol on GPT-5.6-sol High
- **Next ticket:** `NONE`

## Batch A acceptance

The reviewer accepts integration commit `a5699e7b60e3123be1514021d796b1d927c58698`,
publication commit `f219b02edf4b2c8469bdd93d5ba6116b43baedc3`, and the two separate real
price-state products. The integrated production, CLI and test files match all three Review-474
hashes exactly. Commit scopes match the authorized paths. Hermes reports 50/50 focused tests,
Ruff, repository control and whitespace checks passing, followed by one local conversion with
exit 0 in 3,479 seconds.

| Accepted product | Completion SHA-256 | Product rows | Data partitions | Gap artifacts |
|---|---|---:|---:|---:|
| `binance_usdm_funding_indicative_1h` | `360eb662ab89c47ca1f6db754b74f486a42de4aa116970221f0739268a51fba0` | 15,153,756 | 21,507 | 1,115 |
| `binance_usdm_mark_index_basis_1h` | `b698c0543c281e3244e0c3358ea7ce1f347bc591b06a076058fed749d05584f0` | 15,125,823 | 21,491 | 4,181 |

The reviewer independently read all 96,590 descriptor-referenced files and compared them with
the complete filesystem inventory. Both completion hashes, every Parquet and lineage hash,
contained regular-file paths, every actual Arrow schema, row totals, source-reference mappings,
join-run ordinals/timestamps, typed-gap equations, identity states and completion inventories
passed. No unreferenced file or staging file was found. This was read-only reviewer inspection;
the reviewer executed no normalizer or acceptance command.

Indicative source and product rows reconcile at 15,153,756, comprising 6,495,940 negative,
5,661,617 zero and 2,996,199 positive premium closes. All indicative rate values are null with
the declared unavailable status. This preserves observed premium; it does not invent a funding
rate. Its 1,215 typed gap rows explain 48,117 missing hourly grid points.

Basis reconciles `47,279,134 = 3 * 15,125,823 + 1,901,665` physical source rows, with zero
collapsed, excluded or fabricated rows. The 23,268 source months comprise 21,491 nonempty
product months and 1,777 gap-only months. Its 4,603 typed gap rows explain 1,415,967 missing
causal-join grid points. Unmatched source rows split into 1,150,167 mark, 723,565 index and
27,933 premium observations. Native identity and canonical-null state remain exact.

The reviewer separately authenticated nine raw archives and recomputed all 1,694 joined rows
in `0GUSDT/2025-09`, `BTCUSDT/2026-07` and `ETHUSDT/2020-01`. The values, three source times,
original ordinals, absolute basis and signed scale-18 floor arithmetic matched. These include
1,047 negative ratios. For the first 0GUSDT join, mark/premium ordinal 115 matches index ordinal
0; mark close `3.26293867` and index close `3.49374` produce absolute basis `-0.23080133` and
relative basis `-0.066061392662304580`. Close-derived availability remains declared at close.

| Actual bytes | Indicative | Basis |
|---|---:|---:|
| Data Parquets | 635,438,888 | 1,629,242,989 |
| Data lineages | 39,318,800 | 101,269,197 |
| Gap Parquets | 4,088,456 | 15,445,341 |
| Gap lineages | 1,436,213 | 14,460,578 |
| Completion | 14,169,339 | 15,930,704 |
| **All referenced artifact bytes** | **694,451,696** | **1,776,348,809** |
| Pinned product allocation in the completion | 1,673,172,337 | 3,312,444,308 |

Both artifact totals are below their existing allocations. No sizing or schema amendment is
needed. No accepted data is reopened or rerun.

## Record 475 corrections

This review supersedes the following reporting errors without rewriting Hermes's historical
implementation record:

- Record 475 and CURRENT_TASK prematurely claimed product acceptance, which is exclusive to
  the reviewer. Review 474 accepted source and authorized execution; this review accepts data.
- The pair is two products. The count becomes seven, not six; open-interest acceptance is
  Review 445. The fixed eleven-product checklist remains unchanged.
- Record 475 double-counted gap files in its artifact inventory. Indicative has 21,507 data
  Parquets and 21,507 data lineages, plus 1,115 gap Parquets and 1,115 gap lineages, plus one
  completion: 45,245 files. Basis analogously has 51,345 files. The total is 96,590 files,
  not the 102,740 raw-input count copied into CURRENT_TASK.
- The exact integration commit is the 40-character identity above; CURRENT_TASK also carried
  a mistyped copy. The ticket actor field was left at Hermes despite the stated review handoff.
- The reported 7,761,604,608-byte change in shared filesystem free space is not the logical
  artifact total. The independent logical total is 2,470,800,505 bytes; the reported free-space
  delta must not be attributed solely to these artifacts.

The current control records are corrected in place. These errors do not invalidate the verified
data. Batch A is complete; the remaining order stays B liquidation/reconciliation, C cost,
D coverage/intersection/reconciliation/bundle/catalog/readback and final release acceptance.

## Batch B authority and source scope

The reviewer selects Sol High again for this source-author role: its complete Batch A drop is
accepted and the related exact-decimal, authority and immutable-publication work fits the same
senior. Only this senior is authorized. On 2026-09-08 the owner explicitly directs the reviewer
to prompt Sol directly for Batch B. The reviewer may launch and supervise Sol High, receive the
three-file drop, and return consolidated source feedback directly for this assignment. This
supersedes manual owner relay for Batch B and preserves all source-author restrictions and
Hermes's integration/validation/evidence/Git ownership.

Sol may author exactly these three new files:

- `src/cryptofactors/ingest/binance_usdm_liquidation_observed.py`;
- `scripts/research/normalize_binance_usdm_liquidation_observed.py`; and
- `tests/ingest/test_binance_usdm_liquidation_observed.py`.

Build the complete observed-liquidation normalizer and its bounded secondary-source comparison
in this drop. Existing normalizers, acquisition/sizing code, package exports and tests are
read-only references; no shared-framework refactor is authorized. This assignment executes
Batch B of Review 474 and creates no replacement ticket, source universe or storage version.

Use the existing relative generation-0 state/content paths, report SHA-256
`f27b2ba7e6eff3a8b1385d985c49ee64ef60a394737b1246130d0f37b9015f09`, sizing SHA-256
`3995a5072a7d84baecae677ceff6e1c7af9dd076daadec04a31717ffc8f16589`, and seal head
`8875338d0a2b7984fb8fefd7a716a04486667cfb1d726c3758f5496f065ef7ab` already fixed in Review
474. Reprove the terminal chain, complete plan/completion envelope and exact Coinalyze source
selection before use. Coinalyze response SHA-256 authority must not be mislabeled as a Binance
provider checksum sidecar.

The reviewer authenticated all 570 completed Coinalyze response files read-only:

- one `retained_inventory` response, 1,449,633 bytes, SHA-256
  `a5f361ecc91ddfe2a7564f7495adbf7a8cbf75d8f7d0c180c13652592c7b1c97`;
- 569 `checksum_verified` liquidation responses, 20,126,995 bytes, one per mapped native
  symbol, each with nonempty history; and
- 479,340 physical observations in 16,373 observed native-symbol/month partitions. The largest
  selected response is 145,272 bytes. All source times are daily-grid, strictly increasing, and
  all long/short amounts are nonnegative and exactly representable at scale 18. No row has both
  sides zero. These counts are reviewer cross-checks; execution must derive them.

All 569 selected mappings have `oi_lq_vol_denominated_in=BASE_ASSET`, `exchange=A`, perpetual
identity and exact `symbol_on_exchange` binding. Preserve each inventory base/quote asset and
provider symbol in lineage. Native symbols can contain Unicode, including `币安人生USDT`;
safe path containment must not become an invented ASCII-only universe restriction.

Keep all 202 report-declared `coinalyze_symbol_unmapped` gaps and all 771 accepted native
identities. Retained Gate-1 liquidation samples are qualification/sizing evidence, not additional
full-history product inputs. Do not duplicate those points into the 569 acquired responses.

## Frozen product behavior

Publish `binance_usdm_liquidation_observed_daily` with the exact existing 15-column schema,
SHA-256 `7a35b6abb2688ae6b2b79a187172d0a574a65da60f7829148fca13a4c0f794d6`, from
`binance_usdm_harmonic_sizing.py`. The accepted sizing has 486,056 projected points, 16,419
projected partitions and 187,270,569 normalized bytes; those are bounds, not fabricated rows.

1. Authenticate no-follow contained raw files, exact size/hash, returned provider symbol,
   native mapping, plan path/query/params, inclusive requested time bounds, revision point
   count/status, retrieval time and the pinned inventory. Parse JSON with exact numeric lexemes;
   reject floats introduced by a decoder, booleans as numbers, missing fields, non-finite,
   overflow, negative amounts, invalid time grids, duplicate keys and conflicting observations.
2. Preserve long and short **base-asset amounts** and original response point ordinals. Compute
   `liquidation_imbalance = long_liquidation - short_liquidation` with scale-18 integers, positive
   for long-side dominance. This is an amount difference, not a normalized ratio or USD notional.
   No imputation, conversion to USD, rounding or silent row exclusion is authorized.
3. Preserve `source_interval_seconds=86400`,
   `observation_semantics=censored_observed_daily_aggregate`, `event_complete=false`, native
   identity and the existing explicit canonical-null state. Bind the post-2021-04-27 censorship
   rule in product metadata without asserting completeness earlier. A daily event label is not
   an availability timestamp; unknown availability stays unknown, and daily aggregates are
   close-derived observations. Attribute Coinalyze and retain units once per source mapping.
4. Record missing daily runs as typed gaps and the 202 unmapped identities as explicit authority
   gaps. Reconcile every response, physical/output/duplicate row and original point ordinal.
   Never publish an empty successful data partition or turn missing history into zero amounts.
5. Reuse content-addressed partition/lineage/gap publication, no-clobber, same-filesystem
   fsync/rename, deterministic replay and last-written sole completion under a caller-selected
   hidden root. Include comparison evidence and authority gaps in its pinned descriptor. No
   visible bundle or catalog publication occurs. Keep at most one bounded source response plus
   one symbol/month's typed output rows; do not retain the whole product's market rows.

The CLI takes explicit generation-0 state/content-root, report, sizing, accepted bar/OI/funding
product-root and output-root paths, and prints concise completion/row/partition/gap/comparison
counts. Parsing limits must be finite and comfortably cover the authenticated response sizes
and requested daily calendar bounds, without a new acquisition or dependency.

## Required bounded secondary-source comparison

Implement the existing Gate-4 price/OI/funding comparison alongside normalization. Use only the
three raw overlap responses pinned in the report's Coinalyze provenance and their recorded
path/hash/request/retrieval identities:

| Endpoint | SHA-256 under `data/cex002_qualify/coinalyze_cache/` |
|---|---|
| `/ohlcv-history` | `c86e86e868400d6147ea4b41f23afe0d3a381ed1b23673e94335234f895538e6` |
| `/open-interest-history` | `019d0028d675e5a5daf746492ca737f86e4a14df08ce8874c747dc1ea2f83b7b` |
| `/funding-rate-history` | `149c9fcb443ac008f9f7b54ccec57f58a9e1d397063d6c9771c847369187da09` |

The official product completions to authenticate are:

- bars under `data/.cex002_bar_1h`: `3b803d3e84e5d0bf87064626cc0504e9ff92e225a53ba83cdd4e09c38a2e9fd7`;
- OI under `data/.cex002_open_interest_5m`: `bb089fc992326c66ddb65cea03dda92e8cd9fcf7cb7f373821f04a16db9168e4`;
- funding under `data/.cex002_funding_realized`: `57628164f19d182164b6058d9e51f794430cc918706c088f430e1c01d2898522`.

Freeze the comparison days at 2020-10-01, 2020-11-15 and 2020-12-31 for BTCUSDT and ETHUSDT.
Do not select dates after seeing whether they match. Authenticate the exact official partitions
and lineage used, and retain both sides' original timestamps, ordinals and hashes in comparison
evidence. Never silently select a later official day or forward-fill an absent value.

- Price: compare Coinalyze daily `c` with the final official hourly trade-bar close in that UTC
  day. The six reviewer examples match exactly. No mark-price substitution is needed.
- Funding: compare daily `c / 100` with the last actual official settlement rate in the UTC day,
  preserving its original millisecond timestamp. The six observed pairs match exactly and their
  official settlement intervals are all eight hours. The reviewer fixes this percentage-to-
  fractional-rate convention for these comparisons; it does not normalize arbitrary settlement
  intervals, sum daily rates, or treat indicative rates as settlements. Coinalyze's public
  [funding display](https://coinalyze.net/bitcoin/funding-rate/) uses percentages; its
  [API documentation](https://api.coinalyze.net/v1/doc/) distinguishes observed and predicted
  endpoints. Record the comparison convention explicitly.
- OI: compare BTCUSDT daily `c` in base units with the last official same-day OI stock, retaining
  both the daily interval and the official 23:55 observation time. Also record same-day official
  stock min/max. The reviewer observed secondary-minus-official differences of `122.388`,
  `0.012` and `-95.819` base units on the three days. The daily close and five-minute stock have
  different sampling granularity; that can explain differences but does not prove their cause.
  Publish exact values and differences for reviewer disposition; do not invent a tolerance or
  label them an equality PASS.
- ETHUSDT official OI starts in 2021-12, after the retained 2020 overlap receipts. Publish three
  explicit `official_overlap_unavailable` comparison entries. Do not erase them, substitute
  another date/venue or claim all requested comparisons passed. BTC supplies the declared OI
  overlap; the ETH absence remains visible in the release evidence.

The expected comparison inventory is 18 requested entries: 12 exact price/funding pairs, three
measured OI differences and three unavailable OI entries. These are source-review observations,
not permission to hard-code outcomes. Runtime derives values and gaps. The final comparison
disposition remains reviewer-owned; a hidden normalization completion does not itself accept
the secondary source, Gate 4 or the liquidation product.

Comparison arithmetic must also preserve exact values independently of the ambient decimal
context. Exact decimal strings or integer numerator/denominator pairs may carry comparison
differences in JSON without forcing them through a rounded product field.

## Test-source coverage and stop

Cover the fixed schema and actual numeric JSON shape; exact source amounts/difference and units;
Unicode/native/provider mapping; strict envelopes, raw paths/hashes, inventory and overlap
receipt refusal; inclusive query bounds and day/month ownership; source ordinals across months;
missing versus observed zero; unmapped and daily gaps; duplicate/conflict handling; censorship
and availability; bounded retention; immutable interruption/concurrency/replay; percentage
conversion and unmodified settlement milliseconds; same-day OI difference; and explicit absent
ETH overlap. A missing official partition must not become a passing zero or a substituted date.

Return the complete three files with SHA-256 and line counts for one consolidated source review.
Sol performs no tests, linters, compilers, real-data execution, network/acquisition, integration,
repository records, Git, commits, pushes or other-path changes. No additional senior or later
batch is authorized. Hermes integration and execution await reviewer source acceptance.

## Reviewer publication scope

Under the AGENTS.md reviewer governance-publication exception, this review publishes exactly:

- `research/sprint_004/476_CEX002_PRICE_STATE_ACCEPTANCE_AND_LIQUIDATION_SOURCE_AUTHORIZATION.md`;
- `docs/handoff/CURRENT_TASK.md`; and
- `tickets/CEX-002.md`.

Developer source/tests, Record 475, raw and normalized data, and unrelated dirty paths remain
untouched and unstaged. CEX-002 stays `IN_PROGRESS`; the next ticket remains `NONE`.
