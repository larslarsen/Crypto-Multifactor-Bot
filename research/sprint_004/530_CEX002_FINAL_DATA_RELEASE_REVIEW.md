# CEX-002 Review530 — consolidated data delivery and remaining software acceptance

Reviewer: Lead Quantitative Finance Researcher/Engineer. Date: 2026-10-27 UTC.
Disposition: bounded economic evidence ACCEPTED; full-ticket acceptance WITHHELD.
CEX-002 remains IN_PROGRESS; next ticket NONE.

## What is delivered

All eleven required products exist in the admitted release and are readable in place
through Harmonic Trader. The prior full Nautilus catalog roundtrip and subsequent
file/catalog verification remain accepted. Dated contract selection includes all 200
closed or snapshot-missing names. The remaining OI and funding examples now pass.
No acquisition, market-file rewrite, normalization or full verification was repeated.

The original repository-wide pytest requirement has no successful result. Its stopped
retry contains seven failure markers and no failure names or tracebacks. These cannot
be dismissed as unrelated DEX failures. This report does not waive that requirement,
claim all code is healthy, or turn an incomplete run into a pass. The usable data and
accepted consumer delivery remain available while that software evidence is unresolved.

The reader's documented commands and API are in
[Harmonic Trader README](/home/lars/Harmonic_Trader/README.md).
All-product streaming is available; the CLI display limit is not a dataset-size limit.
Real callback checks are recorded in Reviews525–529. No model, orders or fills were run.

## Fixed release and counts

- Admitted publication: `5ea22270b71064c94c4f6dc60f3f045219742a3130cfdb1293b6cbe47a99a30d`.
- Prepared candidate: `8b46bebac377331a08ff1755f2a2c5362f47994939b61837542dfc9628bc9c34`.
- Full consumer proof: `3be8597604efc7353935d79fd663efd7ffa6083ede10f4807d458b9e76927c8d`.
- Original producer commit: `1f5629badfa0e8af6338fbeb019a5f7e60b6a324`.
- Runtime source SHA: `857aec234bc5ebb5905a32d6383fb7f7d59cbf8dbf6da435c5042fd1b095041b`.
- Replay checker SHA: `ac83cc25af508b75fb79d85ba7a615041235f9a9835bb37cb81f9f2f7b740117`.
- Accepted consumer environment: NautilusTrader `2.0.0rc3`.
- Prospective holdout: `2026-08-21T16:19:08.994166+00:00`.

The following totals come from authenticated existing manifests. They agree with the
accepted full proofs; this continuation did not scan all data again. **Table rows include
reference, gap and policy rows, not just market observations.** File counts include
lineage and completion metadata. Bytes exclude raw archives, catalog DB and unrelated files.

| Product (`binance_usdm_` prefix) | Table rows | Files | Bytes |
|---|---:|---:|---:|
| perpetual_membership | 771 | 1,543 | 6,393,517 |
| bar_1h | 16,033,623 | 45,269 | 1,037,394,101 |
| trade_flow_1h | 16,033,623 | 45,269 | 1,613,201,079 |
| open_interest_5m | 160,205,946 | 39,491 | 15,012,407,017 |
| funding_realized | 2,683,024 | 42,071 | 172,919,483 |
| funding_indicative_1h | 15,154,971 | 45,245 | 694,451,696 |
| mark_index_basis_1h | 15,130,426 | 51,345 | 1,776,348,809 |
| liquidation_observed_daily | 484,168 | 37,890 | 136,197,937 |
| cost_calibration | 939,131,092 | 7,732 | 17,943,795,556 |
| coverage_gap | 80,279 | 107,590 | 543,901,501 |
| harmonic_bundle | 178,946 | 1 | 13,232,150 |
| **Total** | **1,165,116,869** | **423,446** | **38,950,242,846** |

[Machine-readable evidence](cex002_final_release_530.json) contains every product's
dataset/manifest/completion/schema identities, component row/file/byte counts, quality
summaries and the candidate's authority pins. Manifest logical identity and whole-file
hash are preserved separately. Attachment SHA256:
`749a28d7ffdd5f9ae530455855de61afc1bac14921500d36577fa54603dbff6d`.

## New economic evidence — PASS, bounded to six partitions

Selection was deterministic: earliest, median-index and latest nonempty BTCUSDT month
in each accepted OI/funding completion descriptor. The helper authenticated the selected
Parquet and lineage bytes against admitted manifests, nine raw ZIPs against retained
checksum-verified acquisition entries, and checksum sidecars. CSV expansion was bounded
to one expected member per ZIP. Exact Fraction arithmetic used original decimal tokens,
without production arithmetic helpers. The attachment preserves the command, helper
source, selection inputs, timestamps, original row ordinals, values and hashes.

`.venv/bin/python /tmp/cex002_closeout530/verify.py` exited 0 in 0.864 seconds:
six partitions, twelve examples, nine raw ZIPs. Both funding signs were present in
every selected funding month. Each selected OI month supplied a gap example.

| BTCUSDT OI month | Adjacent quantity change (BTC) | Adjacent quote-value change (USDT) | Example gap |
|---|---:|---:|---:|
| 2020-09 | 26.182 | -450505.62507218 | 1,500 seconds |
| 2023-09 | 246.888 | 8758654.3173 | 1,200 seconds |
| 2026-08 | -9.913 | -871188.214246 | 1,200 seconds |

Both stock fields equal the raw decimals exactly. Changes equal independent subtraction
across adjacent 300-second observations. At each displayed gap, previous quantity and
both change fields are null. Quote value is the provider-reported notional; this proves
source preservation, not the exchange's underlying valuation method.

| Funding month | Negative source rate | Positive source rate |
|---|---:|---:|
| 2020-01 | -0.00012359 | 0.00003662 |
| 2023-04 | -0.00001240 | 0.00010000 |
| 2026-07 | -0.00000343 | 0.00005532 |

For all six funding examples, time, interval and rate match the raw source exactly;
long cashflow rate is the negative source rate, short rate equals source rate, and
their sum is zero. These are dimensionless settlement-event rates, without annualizing,
interval division, invented positions or claims of actual payment entitlement.

`.venv/bin/python /tmp/cex002_closeout530/summarize.py` exited 0. It authenticated and
summed existing manifest metadata only; it did not reload the 264 MB full consumer proof
or repeat physical/row verification. Failed read-only path/column/interpreter probes
are disclosed separately in the attachment; they are not failed economic comparisons.

## Historical coverage and explicit limits

[Review529](529_CEX002_CONFIRMED_ACTIVE_HISTORY.md) supplies companion
`data/.cex002_contract_history/review529-20261027.json`, SHA256
`6ef47558eff2b3d3b30fbd8569dd96e0f7b7863bd8b310025cf641f7e72034a9`,
1,290,098 bytes, retrospective known_from `2026-10-27T18:20:52Z`.
It covers 782 episodes across 770 names, including all 200 closed/snapshot-missing names.
GAIBUSDT is explicitly postponed/pending with no bar partition. Five names have conservative
confirmed-active starts instead of invented exact launches. Earlier unknown and crossing
bars remain inspectable but are refused by history-aware native projection. The companion
adds identities without rewriting old immutable products' null canonical-ID fields.

The coverage product contains 771 instrument summaries and 64,764 daily report files,
with 1,971,447 aligned symbol-days. The five-product observed intersection is 428,090
symbol-days; 424,431 satisfy fixed-cadence plus event-presence criteria. Neither number
means complete realized-funding schedules or complete liquidation capture. The same
coverage artifact preserves 8,317 qualification-gap rows, 3,742 typed membership-gap rows
and 68,220 quality-gap rows. A gap never erases historical membership.

Bars contain 16,033,469 observations plus 154 gap rows; trade flow contains 16,033,442
observations plus 181 gap rows. Provider-inconsistent inputs remain excluded and sourced,
not repaired. OI contains 160,148,505 observations plus 57,441 gap rows; its accepted
physical-source reconciliation separately accounts for 75,255 identical repeats and
2,818 spillovers. Realized funding preserves 2,683,024 events without inferred settlements.
Indicative funding has 1,215 gap rows; unavailable actual indicative rates remain null.
Mark/index/basis has 4,603 gap rows; causal calculations are covered by Records475/476.

Observed liquidation has 479,340 observations, 4,626 missing-input rows and 202 unmapped
identities. It remains censored/observed; missing is never zero. Secondary-source overlap
had 12 exact price/funding comparisons, three BTC OI differences (122.388, 0.012 and -95.819)
within the corresponding official daily ranges, and three unavailable official ETH OI
comparisons. It was not 18 exact matches. The immutable pre-review metadata value
`comparison_disposition: pending_reviewer` is resolved by Review476's external acceptance,
not by editing the product.

Cost data contains 939,130,319 book observations, 771 historical-fee gaps and two explicit
nonbackdated scenario policies. There are zero sourced official historical fee-schedule
rows and 494 frozen cost-source gaps. Review480 accepts exact source/inventory reconciliation
after a ticker projection underestimated rows by 136,532,583; the original sizing failure
remains a failure. Cost samples are not continuous historical order books.

Historical receipt times, complete fee history and complete dated order/margin constraints
remain unavailable. Present constraints must not be carried backward. Event-time playback
and reviewed-notice continuity are explicit assumptions. Native callbacks establish data
delivery and dated selection, not realistic fills, order acceptance or funding entitlement.
Review529 explains why additional public-notice crawling cannot recover unannounced changes.

## Acceptance evidence map

Original commands and terminal outputs remain in the linked execution records; they were
not replayed here. Later accepted corrections do not relabel earlier failures as passes.

| Requirement | Evidence and disposition |
|---|---|
| Gate0: five false artifacts excluded; normalizer corrected | [Review485](485_CEX002_GATE0_QUARANTINE_SOURCE_REVIEW.md), [Record486](486_CEX002_GATE0_QUARANTINE_INTEGRATION_RECORD.md), [Review487](487_CEX002_BITMEX_NORMALIZER_SOURCE_REVIEW.md), [Record488](488_CEX002_BITMEX_NORMALIZER_INTEGRATION_RECORD.md): accepted. Record524 confirms five excluded catalog rows, digest `b4334b2c3f28d58a288b0130e1009dd305c5cf30b7e4af734f8036bd74d82103`. |
| Gate1: historical discovery, qualification and sizing | [Review179](179_CEX002_GATE1_ACCEPTANCE_AND_STORAGE_SIZING_ARCHITECTURE.md) and accepted authority pins in the attachment. Qualification SHA `f27b2ba7e6eff3a8b1385d985c49ee64ef60a394737b1246130d0f37b9015f09`; sizing SHA `3995a5072a7d84baecae677ceff6e1c7af9dd076daadec04a31717ffc8f16589`. |
| Gate2: retained raw acquisition and resume | [Review415](415_CEX002_RECORD414_ACCEPTANCE_GATE2_AND_OPEN_INTEREST_AUTHORIZATION.md): accepted 685,072 generation-0 objects and 51,274 recovery objects; one explicit HBARUSDC 2026-07-09 checksum conflict, totaling 736,347 planned Binance objects. Coinalyze: 570 completions and 202 mapping gaps. |
| Gate3: eleven products and economic semantics | [OI445](445_CEX002_OPEN_INTEREST_PRODUCT_ACCEPTANCE.md), [bars/flow460](460_CEX002_HOURLY_KLINE_PRODUCT_ACCEPTANCE.md), [membership465](465_CEX002_MEMBERSHIP_PRODUCT_ACCEPTANCE.md), [funding473](473_CEX002_REALIZED_FUNDING_ACCEPTANCE.md), [price/liquidation476](476_CEX002_PRICE_STATE_ACCEPTANCE_AND_LIQUIDATION_SOURCE_AUTHORIZATION.md), [cost480](480_CEX002_COST_ACCEPTANCE_AND_COVERAGE_SOURCE_AUTHORIZATION.md), [coverage483](483_CEX002_COVERAGE_RECONCILIATION_RECOVERY_REVIEW.md), [bundle510](510_CEX002_SHARED_SCHEMA_BUNDLE_PREPARATION_RESUME_RECORD.md), and this review's OI/funding evidence. All product components accepted. |
| Gate4: minute/hour, secondary source and coverage | [Record490](490_CEX002_KLINE_RECONCILIATION_INTEGRATION_AND_RUN_RECORD.md)/[Review491](491_CEX002_EMPTY_MINUTE_OPEN_CORRECTION_REVIEW.md): corrected 2,672/2,672 fields across 167 complete hours, nine days/ten roles; three partial and 46 absent hours explicitly uncomparable. [Record477](477_CEX002_LIQUIDATION_INTEGRATION_AND_REAL_RUN_RECORD.md): all observed liquidation values/imbalances and 18 bounded overlap cases. [Record484](484_CEX002_COVERAGE_RECONCILIATION_AND_REPLAY_RECORD.md): accepted complete coverage/replay. New OI/funding evidence completes the enumerated examples. |
| Gate5: publication, full consumer and replay | [Record518](518_CEX002_FULL_CONSUMER_EXECUTION_RECORD.md)/[Review517](517_CEX002_FULL_CONSUMER_EXECUTION_AUTHORIZATION.md): accepted full 1,165,116,869-row roundtrip. [Record520](520_CEX002_CATALOG_ADMISSION_AND_REPLAY_RECORD.md)/[Review519](519_CEX002_CATALOG_ADMISSION_AND_REPLAY_AUTHORIZATION.md): accepted initial admission. [Record524](524_CEX002_KNOWN_RELEASE_REPLAY_READBACK_RECORD.md)/[Review522](522_CEX002_KNOWN_RELEASE_RECONCILIATION_SOURCE_AUTHORIZATION.md): successful 773.097-second replay/readback, exit0, 423,446 files, 11 datasets, 10 dependency links. Failed capacity replay remains FAILED. |
| Historical consumer repair | [Review529](529_CEX002_CONFIRMED_ACTIVE_HISTORY.md): 54 focused cases, scoped lint and actual five-symbol callbacks passed; previous accepted history/consumer checks retained. HT commit `ad33f1a4a3eeeb089bf0eebb51b2085e313adcf7`. |
| Original final pytest | **NOT PASSED.** Initial collection exit2; corrected-environment retry interrupted, pytest exit143, wrapper exit0. Seven unnamed failures through 51% progress. No full result or failure attribution. |
| Original final Ruff/control/whitespace | [Record526](526_CEX002_FINAL_RELEASE_AND_ACCEPTANCE_RECORD.md) preserves actual passes, with the first-failure workflow violation explicitly disclosed. These do not make pytest pass. New publication checks are recorded below. |

The accepted full row proof and the later physical/catalog replay are distinct evidence.
Record524 reused accepted logical values under ADR0040; it was not a second full Nautilus
roundtrip. At that run it recorded 198,410,391,552 free bytes, a 29,690,701,415 operating
reserve and 3,450,808,960 SQLite bytes. These are dated measurements, not current capacity.

## Remaining acceptance issue and bounded next action

The one missing original acceptance item is successful final repository-wide pytest
evidence. Its partial log is now durably embedded in the attachment, not left solely in
`/tmp`. Current pytest caches contain 4,865 node IDs and 113 prior-failure entries; they
are not an authenticated execution-order list for that stopped run. No claim identifies
the seven failures from those caches or attributes them to DEX.

Reviewer next action is read-only attribution from retained run/session records and
test collection/configuration source. Do not rerun the repository-wide suite, use
`--last-failed` on the mixed cache, or launch broad collection. If attribution requires
execution, first enumerate the exact relevant tests and bound the command in the review.
No source correction is assigned without a named defect. A required acceptance change
must be explicit; owner stop instructions do not imply that failed tests passed.

The bounded economic/report assignment is complete. Do not repeat it, contract-history
recovery, full storage proofs or consumer replay on the next continuation. No new ticket,
model, acquisition, market-data mutation, cleanup or unrelated DEX work is authorized.

## Publication scope

Under the owner's repair override, reviewer publication is exactly:

- `research/sprint_004/530_CEX002_FINAL_DATA_RELEASE_REVIEW.md`
- `research/sprint_004/cex002_final_release_530.json`
- `docs/handoff/CURRENT_TASK.md`
- `tickets/CEX-002.md`

Only repository-control and whitespace checks apply to this evidence-only publication.
Preserve unrelated dirty paths. Stage exactly these four paths, inspect the staged set,
commit/push, and verify HEAD equals origin/main with an empty index. No HT files change.

Publication validation: `python3 scripts/check_repo_control.py` and the exact four-path
`git diff --check` exited 0. Attachment SHA, count equations and all report links were
checked successfully. No test suite or data execution was repeated for publication.
