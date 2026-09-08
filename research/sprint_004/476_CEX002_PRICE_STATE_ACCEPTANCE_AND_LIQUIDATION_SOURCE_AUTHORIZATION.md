# CEX-002 Review 476 - Price-State Acceptance and Liquidation Source Authorization

- **Date:** 2026-09-08
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** accept both Batch A products; freeze corrected Batch B production/CLI and require the single test-fixture correction below
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

The exact inclusive request ranges contain 486,056 daily slots: 479,340 observed and 6,716
missing. Their 16,419 native-symbol/month union contains 46 wholly gap-only months. The reviewer
counted 4,566 maximal missing runs before month splitting. These source-review facts explain the
observed-versus-projected difference without changing any bound or inventing output rows.

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
4. Derive missing daily runs over each authenticated inclusive request range, including leading,
   trailing and whole-month absences, and publish typed gaps. Keep the 202 unmapped identities as
   separate authority gaps. Reconcile every response, physical/output/duplicate row and original
   point ordinal. Never publish an empty successful data partition or turn missing history into
   zero amounts.
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

## Consolidated Batch B source review and corrective authorization

The reviewer inspected the complete frozen drop, including the final static amendments, and
does not yet accept it for integration. The returned identities are:

| Path | SHA-256 | Lines |
|---|---|---:|
| `src/cryptofactors/ingest/binance_usdm_liquidation_observed.py` | `0974dc6750f4e3211af44402ea29febc818f2e1371b63b93ad34f255cf7c27cd` | 1,039 |
| `scripts/research/normalize_binance_usdm_liquidation_observed.py` | `8d97b52138c1ff27a39ddcc5b3fbb99f7db774ba5d0c948103d9d9b95830cfee` | 54 |
| `tests/ingest/test_binance_usdm_liquidation_observed.py` | `f1f7919f85a4f42b64a135e7455d2f186d3a03212cbc737cba6ba827ee33d20e` | 423 |

Sol's final static amendments fixed the receipt field names, context-independent scale-18
construction, exact OI extrema, SQLite sidecar checks, official schema/lineage checks and
comparison timestamps. Those are not outstanding findings. No runtime result is claimed.

The same Sol High actor is authorized to correct only the production and test paths above.
The CLI is frozen at its returned hash. This is one consolidated correction against the existing
contract, with no new product, schema, authority, architecture or acceptance gate:

1. **Match the retained inventory.** `_inventory_mappings` requires every Binance perpetual to
   equal `native + "_PERP.A"` and use base units. The real inventory contains 759 Binance
   perpetual mappings, including 20 already-suffixed coin-margined native identities using quote
   units. For example, `AAVEUSD_PERP` maps to `AAVEUSD_PERP.A`. Reproduce the existing
   `coinalyze_perp_symbol` mapping rule and all 759 mappings for digest
   `915b643adb226699d9b8fd4607e727470114ccf44b9bb9665a9035acdfc1565c`.
   Apply the required base-unit and selected-product checks to the 569 selected mappings. Do not
   reject or remove unrelated inventory entries, nor add them to the liquidation universe.
2. **Match the acquired request identities.** Both `_validate_raw_descriptor` and
   `load_generation0_authority` invent a `coinalyze:` prefix on liquidation identities; only the
   inventory identity has that prefix. The actual first liquidation identity begins
   `/liquidation-history?symbols=0GUSDT_PERP.A&interval=daily&from=1758067200&to=1787356800&convert_to_usd=false`.
   Its payload URL is `https://api.coinalyze.net/v1/liquidation-history`, with query and params in
   separate fields. The current `url + "?" + query` check rejects every actual plan. Bind the
   exact existing forms and retain strict parameter/revision types, path containment and the
   terminal seal. Complete the inventory accepted-path, retained revision and retrieval binding
   against its pinned report receipt. Correct fixtures must exercise these real shapes.
3. **Verify the bytes consumed and published.** `_official_rows` hashes one opened file and
   then reopens its pathname for Parquet consumption. Read the authenticated bytes or retain
   the authenticated descriptor. `_OutputTree.publish` does not verify the final file after a
   successful rename, and the stored root identity is never checked. A staged-file replacement
   or root rename can therefore return a digest/path that does not identify the published data.
   Restore held-root/path verification and final regular-file/hash/schema/row verification for
   Parquets and final byte verification for JSON, including comparison and completion. Preserve
   no-clobber, fsync, replay and completion-last behavior; an altered stage, winner or held root
   must not produce a successful completion. The accepted funding publisher is a read-only
   reference for these existing requirements.
4. **Keep one month's typed rows.** The `by_month` dictionary constructs all typed output rows
   for every month in a response before publishing its first partition. Iterate the bounded raw
   response in month order, build/publish/release one month's typed rows and gaps, and preserve
   global point ordinals. Do not retain all monthly typed buffers. Replace the current GC-count
   assertion with a meaningful buffer-lifetime test; ordinary atomic dictionaries need not appear
   in `gc.get_objects()`, and its two-point fixture does not prove the required monthly bound.
5. **Repair and complete the focused tests.** `_raw` has an unescaped JSON object brace in its
   f-string and cannot build its intended raw response. The interruption test calls `iterdir()`
   on `.complete` before that directory is created. Correct both fixture failures. Cover the
   actual report/inventory/plan/completion shapes and their refusal cases, including the full
   mapping versus selected-unit distinction; the present suite never calls the authority loader
   or report parser. Add focused regressions for item 3's byte/root substitutions, item 4's
   monthly retention, and low-context/max-precision signed imbalance. A test named decoder-float
   refusal must actually pass a decoder float and assert refusal. Preserve the existing gap,
   exact comparison, absent-overlap and immutable replay cases.
6. **Meet the existing Ruff gate.** The production/test files contain many inline suites and
   semicolon-separated statements rejected by the repository's existing E701/E702 defaults,
   plus the unused test `os` import. Expand these into reviewable statements and remove unused
   imports. This is required check compliance, not a new formatting policy. Sol does not run
   Ruff; Hermes retains that check.

After completing this bounded correction and its static pass, the reviewer explicitly authorizes
Sol to run exactly one targeted command, once, from the repository root:

```bash
PYTHONPATH=src /home/lars/Crypto_Multifactor_Bot/.venv/bin/python -m pytest tests/ingest/test_binance_usdm_liquidation_observed.py -q
```

This uses AGENTS.md's targeted senior test exception for immediate corrective source feedback.
Fixture writes belong only to pytest temporary storage. Sol reports the exact command, complete
output, exit code, three final hashes and line counts, then stops. On the first nonzero result,
stop without patching or rerunning. No other runtime check, normalizer, real-data mutation,
network, linter/compiler, integration, record, Git operation or later batch is authorized.
Hermes remains unauthorized pending reviewer source acceptance. Batch A remains accepted;
CEX-002 stays `IN_PROGRESS`, with seven accepted products and next ticket `NONE`.

## Corrective result and single fixture correction

The reviewer accepts the six production/source corrections after static inspection and confirms
the returned hashes. The production and CLI are now frozen:

- Production: `2e001f2d63c6f127d58e7db0c071a2971ecb6a769d5bd1d85b322d085a1ee257`,
  1,491 lines.
- CLI: `8d97b52138c1ff27a39ddcc5b3fbb99f7db774ba5d0c948103d9d9b95830cfee`, 54 lines.
- Test source at the nonzero result:
  `16ab11c890c7cd884836b52322408ec48987cf99e83625d46f6690e77f465c03`, 1,025 lines.

Sol ran the one authorized targeted command once. Exit code was `1`: 45 cases passed and one
failed. The complete reported output was:

```text
...................F..........................                           [100%]
=================================== FAILURES ===================================
______________ test_raw_path_hash_size_and_query_binding_refusal _______________

tmp_path = PosixPath('/home/lars/.cache/tmp/pytest-of-lars/pytest-419/test_raw_path_hash_size_and_qu0')

    def test_raw_path_hash_size_and_query_binding_refusal(tmp_path: Path) -> None:
        raw = _raw(tmp_path)
        for changed, message in (
            (replace(raw, source_sha256="0" * 64), "digest"),
            (replace(raw, byte_size=raw.byte_size + 1), "size"),
            (replace(raw, identity=raw.identity + "x"), "identity"),
            (replace(raw, request_to_s=raw.request_to_s + 1), "daily grid"),
            (replace(raw, point_count=raw.point_count + 1), "point count"),
        ):
>           with pytest.raises(subject.LiquidationNormalizationError, match=message):
                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E           AssertionError: Regex pattern did not match.
E             Expected regex: 'daily grid'
E             Actual message: 'liquidation query identity changed'

tests/ingest/test_binance_usdm_liquidation_observed.py:591: AssertionError
=========================== short test summary info ============================
FAILED tests/ingest/test_binance_usdm_liquidation_observed.py::test_raw_path_hash_size_and_query_binding_refusal
```

The off-grid fixture changes `request_to_s` without updating its query identity, so production
correctly rejects the inconsistent identity before reaching the intended grid check. This is a
fixture defect, not a reason to change validation order or weaken either check. Sol correctly
stopped without patching or rerunning after the nonzero result.

The same Sol High actor may now edit only
`tests/ingest/test_binance_usdm_liquidation_observed.py`, only to make that off-grid fixture's
query identity agree with its intentionally off-grid bound. Retain the `daily grid` refusal
assertion and the separate identity refusal case. All other tests, production and CLI remain
frozen. After this bounded fixture correction, Sol may run the exact targeted pytest command
enumerated above once under the same senior-test exception, report complete output/exit code and
all three hashes/line counts, and stop. On nonzero, do not patch or rerun. No other command or
ownership exception is added. Hermes remains unauthorized until the full source drop is accepted.

## Reviewer publication scope

Under the AGENTS.md reviewer governance-publication exception, this review publishes exactly:

- `research/sprint_004/476_CEX002_PRICE_STATE_ACCEPTANCE_AND_LIQUIDATION_SOURCE_AUTHORIZATION.md`;
- `docs/handoff/CURRENT_TASK.md`; and
- `tickets/CEX-002.md`.

Developer source/tests, Record 475, raw and normalized data, and unrelated dirty paths remain
untouched and unstaged. CEX-002 stays `IN_PROGRESS`; the next ticket remains `NONE`.
