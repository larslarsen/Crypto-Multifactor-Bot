# CURRENT_TASK

Ticket: CEX-002
State: IN_PROGRESS
Next required actor: Sr Dev - Claude Build - implement reviews 294-295 when available
Final reviewer: Lead Quantitative Finance Researcher/Engineer
Next ticket authorized: NONE

Immediate state: review 295 rejects Grok Build's claimed review-294 correction at
source/test hashes `eb9ab7b0...` / `78cc289b...` without tests and deauthorizes Grok after
two partial returns against the same complete contract. The new schema cannot open because
`DOMAIN_CHECKS` queries removed `run_metadata.receipt_sha256`. Most operational paths still
bypass retained roots; state setup leaks local WAL/SHM descriptors on failures; `run_seal`
is not authenticated or emitted in terminal evidence; the chain still checks only one
predecessor; a released charge cannot be reserved again and its sealed ledger includes
refunded bytes; terminal descriptor and inventory equality remain partial; and only six of
the required direct tests were added. Review 294 remains the complete correction contract,
and review 295 adds the concrete residuals introduced or retained by this drop. Claude Build
owns the exact three-path implementation when available. No test may run until the full
source and regression contract is present; Claude then has an at-most-three-run targeted
pytest/repair exception. Hermes still owns integration, broader acceptance commands,
evidence, and developer-source Git. No real plan, network, data, integration, Git,
normalization, catalog, NautilusTrader, Harmonic Trader, PAPER/LIVE, or next-ticket work is
authorized. Next ticket is `NONE`.

Governing documents:

- tickets/CEX-002.md
- docs/adr/0017-free-harmonic-ready-binance-derivatives-data.md
- docs/adr/0029-content-addressed-gate2-acquisition-and-resume.md
- research/sprint_004/286_CEX002_GATE2_ACQUISITION_ARCHITECTURE_AND_SOURCE_AUTHORIZATION.md
- research/sprint_004/287_CEX002_GATE2_FIRST_SOURCE_REVIEW_AND_CONSOLIDATED_CORRECTION.md
- research/sprint_004/288_CEX002_GATE2_CORRECTION_REVIEW_AND_COMPLETE_RESIDUAL_AUTHORIZATION.md
- research/sprint_004/289_CEX002_GROK_RESIDUAL_REJECTION_AND_CLAUDE_REASSIGNMENT.md
- research/sprint_004/290_CEX002_CLAUDE_TARGETED_TEST_FAILURE_AND_CORRECTION.md
- research/sprint_004/291_CEX002_CLAUDE_COMPLETE_STATIC_REVIEW_AND_CONSOLIDATED_CORRECTION.md
- research/sprint_004/292_CEX002_CLAUDE_NONCOMPLIANCE_AND_GROK_REASSIGNMENT.md
- research/sprint_004/293_CEX002_GROK_REPLACEMENT_COMPLETE_STATIC_REVIEW.md
- research/sprint_004/294_CEX002_GROK_CORRECTION_COMPLETE_STATIC_REJECTION.md
- research/sprint_004/295_CEX002_GROK_REVIEW294_NONCOMPLIANCE_AND_CLAUDE_REASSIGNMENT.md
- research/sprint_004/59_CEX001_SOURCE_AND_PLATFORM_REVIEW.md
- research/sprint_004/60_CEX_DATA_DESTINATION_DECISION.md
- research/sprint_004/61_CEX002_SPARK_SOURCE_REVIEW.md
- research/sprint_004/63_CEX002_GROK_SOURCE_REVIEW.md
- research/sprint_004/64_CEX002_GROK_SECOND_SOURCE_REVIEW.md
- research/sprint_004/65_CEX002_CLAUDE_SOURCE_REVIEW.md
- research/sprint_004/66_CEX002_GATE1_EXECUTION.md
- research/sprint_004/67_CEX002_GATE1_EXECUTION_REVIEW.md
- research/sprint_004/68_CEX002_CLAUDE_OPERATIONAL_SOURCE_REVIEW.md
- research/sprint_004/69_CEX002_CLAUDE_CHECKPOINT_SOURCE_REVIEW.md
- research/sprint_004/70_CEX002_CLAUDE_FINAL_SOURCE_REVIEW.md
- research/sprint_004/71_CEX002_GATE1_RESUMABLE_EXECUTION.md
- research/sprint_004/72_CEX002_GATE1_RESUMABLE_EXECUTION_REVIEW.md
- research/sprint_004/73_CEX002_CLAUDE_TEST_SOURCE_REVIEW.md
- research/sprint_004/74_CEX002_GATE1_RESUMABLE_EXECUTION.md
- research/sprint_004/75_CEX002_GATE1_RESUMABLE_EXECUTION_REVIEW.md
- research/sprint_004/76_CEX002_CLAUDE_AUTHORITY_PLAN_SOURCE_REVIEW.md
- research/sprint_004/77_CEX002_CLAUDE_DURABLE_AUTHORITY_SOURCE_REVIEW.md
- research/sprint_004/78_CEX002_CLAUDE_STABLE_AUTHORITY_SOURCE_REVIEW.md
- research/sprint_004/79_CEX002_CLAUDE_TRANSITION_SOURCE_REVIEW.md
- research/sprint_004/80_CEX002_GROK_TRANSITION_SOURCE_REVIEW.md
- research/sprint_004/81_CEX002_GATE1_STABLE_AUTHORITY_EXECUTION.md
- research/sprint_004/82_CEX002_FOCUSED_TEST_FAILURE_REVIEW.md
- research/sprint_004/83_CEX002_SPARK_TEST_SOURCE_REVIEW.md
- research/sprint_004/84_CEX002_SPARK_FINAL_TEST_SOURCE_REVIEW.md
- research/sprint_004/85_CEX002_GATE1_STABLE_AUTHORITY_EXECUTION.md
- research/sprint_004/86_CEX002_TRUNCATED_TEST_SUITE_REVIEW.md
- research/sprint_004/87_CEX002_GROK_RESTORED_TEST_SOURCE_REVIEW.md
- research/sprint_004/88_CEX002_GATE1_STABLE_AUTHORITY_EXECUTION.md
- research/sprint_004/89_CEX002_GATE1_STABLE_AUTHORITY_EXECUTION_REVIEW.md
- research/sprint_004/90_CEX002_GROK_STABLE_IDENTITY_SOURCE_REVIEW.md
- research/sprint_004/91_CEX002_GATE1_CORRECTED_EXECUTION.md
- research/sprint_004/92_CEX002_PLAN_VERSION_2_AUTHORIZATION.md
- research/sprint_004/93_CEX002_GATE1_PLAN2_EXECUTION.md
- research/sprint_004/94_CEX002_PLAN_ROUNDTRIP_REVIEW.md
- research/sprint_004/95_CEX002_GROK_PLAN_ROUNDTRIP_SOURCE_REVIEW.md
- research/sprint_004/96_CEX002_GATE1_PLAN2_EXECUTION.md
- research/sprint_004/97_CEX002_GATE1_PLAN2_EXECUTION_REVIEW.md
- research/sprint_004/98_CEX002_RESOLUTION_AND_STORAGE_ARCHITECTURE_REVIEW.md
- research/sprint_004/99_CEX002_GROK_RESOLUTION_SOURCE_REVIEW.md
- research/sprint_004/100_CEX002_CLAUDE_CANDIDATE_SOURCE_REVIEW.md
- research/sprint_004/101_CEX002_CLAUDE_LINEAGE_SOURCE_REVIEW.md
- research/sprint_004/102_CEX002_CLAUDE_CLI_PREFLIGHT_SOURCE_REVIEW.md
- research/sprint_004/103_CEX002_PLAN3_CANDIDATE_SOURCE_ACCEPTANCE.md
- research/sprint_004/104_CEX002_PLAN3_CANDIDATE_EXECUTION.md
- research/sprint_004/105_CEX002_FOCUSED_FAILURE_REVIEW.md
- research/sprint_004/106_CEX002_FOCUSED_CORRECTION_SOURCE_ACCEPTANCE.md
- research/sprint_004/107_CEX002_PLAN3_CANDIDATE_EXECUTION.md
- research/sprint_004/108_CEX002_RESIDUAL_FOCUSED_FAILURE_REVIEW.md
- research/sprint_004/109_CEX002_RESIDUAL_CORRECTION_SOURCE_ACCEPTANCE.md
- research/sprint_004/110_CEX002_PLAN3_CANDIDATE_EXECUTION.md
- research/sprint_004/111_CEX002_HOLDOUT_RECORD_PATH_FAILURE_REVIEW.md
- research/sprint_004/112_CEX002_RECORD_PATH_SOURCE_ACCEPTANCE.md
- research/sprint_004/113_CEX002_PLAN3_CANDIDATE_EXECUTION.md
- research/sprint_004/114_CEX002_CANDIDATE_TIMEOUT_REVIEW.md
- research/sprint_004/115_CEX002_PLAN3_CANDIDATE_RESUME.md
- docs/adr/0018-resumable-bounded-listing-execution.md
- research/sprint_004/116_CEX002_LISTING_EXECUTION_ARCHITECTURE_REVIEW.md
- research/sprint_004/117_CEX002_LISTING_SOURCE_REVIEW.md
- research/sprint_004/118_CEX002_LISTING_CORRECTION_SOURCE_REVIEW.md
- research/sprint_004/119_CEX002_LISTING_RESIDUAL_TEST_REVIEW.md
- research/sprint_004/120_CEX002_LISTING_SOURCE_ACCEPTANCE.md
- research/sprint_004/121_CEX002_LISTING_INTEGRATION_AND_CANDIDATE_RESUME.md
- docs/adr/0019-scalable-qualification-evidence-publication.md
- research/sprint_004/122_CEX002_TERMINAL_REPORT_ARCHITECTURE_REVIEW.md
- research/sprint_004/123_CEX002_REPORT_SPLIT_SOURCE_REVIEW.md
- research/sprint_004/124_CEX002_GROK_REPORT_SPLIT_CONTINUATION.md
- research/sprint_004/125_CEX002_GROK_REPORT_SPLIT_RESIDUAL_REVIEW.md
- research/sprint_004/126_CEX002_REPORT_SPLIT_SOURCE_ACCEPTANCE.md
- research/sprint_004/127_CEX002_REPORT_SPLIT_INTEGRATION_AND_CANDIDATE.md
- research/sprint_004/128_CEX002_FOCUSED_TEST_FAILURE_REVIEW.md
- research/sprint_004/129_CEX002_SPARK_TEST_SOURCE_REVIEW.md
- research/sprint_004/130_CEX002_SPARK_TEST_SOURCE_ACCEPTANCE.md
- research/sprint_004/131_CEX002_TEST_INTEGRATION_AND_CANDIDATE.md
- research/sprint_004/132_CEX002_RUFF_FAILURE_REVIEW.md
- research/sprint_004/133_CEX002_RUFF_SOURCE_ACCEPTANCE.md
- research/sprint_004/134_CEX002_RUFF_INTEGRATION_AND_CANDIDATE.md
- research/sprint_004/135_CEX002_TERMINAL_CANDIDATE_REVIEW.md
- research/sprint_004/136_CEX002_RECORD_134_CORRECTION.md
- docs/adr/0020-historical-contract-authority-and-qualification-budget.md
- research/sprint_004/137_CEX002_MEMBERSHIP_AND_BUDGET_ARCHITECTURE.md
- research/sprint_004/138_CEX002_CLAUDE_ADR0020_SOURCE_REVIEW.md
- research/sprint_004/139_CEX002_CLAUDE_ADR0020_CORRECTION_REVIEW.md
- research/sprint_004/140_CEX002_ADR0020_SOURCE_ACCEPTANCE.md
- research/sprint_004/141_CEX002_ADR0020_INTEGRATION_AND_CANDIDATE.md
- research/sprint_004/142_CEX002_FOCUSED_TEST_FAILURE_REVIEW.md
- research/sprint_004/143_CEX002_FOCUSED_TEST_SOURCE_ACCEPTANCE.md
- research/sprint_004/144_CEX002_FOCUSED_TEST_INTEGRATION_AND_CANDIDATE.md
- research/sprint_004/145_CEX002_VERSION4_CANDIDATE_REVIEW.md
- research/sprint_004/146_CEX002_CLAUDE_MIGRATION_SOURCE_REVIEW.md
- research/sprint_004/147_CEX002_GROK_MIGRATION_CONTINUATION.md
- research/sprint_004/148_CEX002_GROK_MIGRATION_SOURCE_REVIEW.md
- research/sprint_004/149_CEX002_GROK_MIGRATION_RESIDUAL_REVIEW.md
- research/sprint_004/150_CEX002_SPARK_MIGRATION_TEST_REVIEW.md
- research/sprint_004/151_CEX002_MIGRATION_SOURCE_ACCEPTANCE.md
- research/sprint_004/152_CEX002_MIGRATION_INTEGRATION_AND_EXECUTION.md
- research/sprint_004/153_CEX002_MIGRATION_FOCUSED_FAILURE_REVIEW.md
- research/sprint_004/154_CEX002_MIGRATION_TEST_SOURCE_ACCEPTANCE.md
- research/sprint_004/155_CEX002_MIGRATION_TEST_INTEGRATION_AND_EXECUTION.md
- research/sprint_004/156_CEX002_MIGRATION_RUFF_FAILURE_REVIEW.md
- research/sprint_004/157_CEX002_MIGRATION_RUFF_SOURCE_ACCEPTANCE.md
- research/sprint_004/158_CEX002_MIGRATION_RUFF_INTEGRATION_AND_EXECUTION.md
- research/sprint_004/159_CEX002_MIGRATION_NETWORK_FAILURE_REVIEW.md
- research/sprint_004/160_CEX002_MIGRATION_NETWORK_RETRY.md
- research/sprint_004/161_CEX002_MIGRATION_ACCEPTANCE_AND_SAMPLE_EXECUTION.md
- research/sprint_004/162_CEX002_VERSION4_SAMPLE_EXECUTION.md
- research/sprint_004/163_CEX002_SAMPLE_OUTCOME_ARCHITECTURE_REVIEW.md
- research/sprint_004/164_CEX002_CLAUDE_SEMANTIC_AUTHORITY_SOURCE_REVIEW.md
- research/sprint_004/165_CEX002_CLAUDE_AUTHORITY_RESIDUAL_REVIEW.md
- research/sprint_004/166_CEX002_CLAUDE_AUTHORITY_TEST_REVIEW.md
- research/sprint_004/167_CEX002_AUTHORITY_SOURCE_ACCEPTANCE.md
- research/sprint_004/168_CEX002_AUTHORITY_SOURCE_INTEGRATION.md
- research/sprint_004/169_CEX002_AUTHORITY_IMPORT_FAILURE_REVIEW.md
- research/sprint_004/170_CEX002_AUTHORITY_IMPORT_SOURCE_ACCEPTANCE.md
- research/sprint_004/171_CEX002_AUTHORITY_IMPORT_INTEGRATION.md
- research/sprint_004/172_CEX002_AUTHORITY_FOCUSED_FAILURE_REVIEW.md
- research/sprint_004/173_CEX002_AUTHORITY_TEST_SOURCE_ACCEPTANCE.md
- research/sprint_004/174_CEX002_AUTHORITY_TEST_INTEGRATION.md
- research/sprint_004/175_CEX002_AUTHORITY_TRANSACTION_AUTHORIZATION.md
- research/sprint_004/176_CEX002_AUTHORITY_TRANSACTION_EXECUTION.md
- research/sprint_004/177_CEX002_CORRECTED_QUALIFICATION_AUTHORIZATION.md
- research/sprint_004/178_CEX002_CORRECTED_QUALIFICATION_EXECUTION.md
- docs/adr/0021-bounded-real-sample-storage-sizing.md
- research/sprint_004/179_CEX002_GATE1_ACCEPTANCE_AND_STORAGE_SIZING_ARCHITECTURE.md
- research/sprint_004/181_CEX002_CLAUDE_STORAGE_SIZING_SOURCE_REVIEW.md
- research/sprint_004/182_CEX002_CLAUDE_STORAGE_SIZING_CORRECTION_REVIEW.md
- research/sprint_004/183_CEX002_CLAUDE_STORAGE_SIZING_RESIDUAL_REVIEW.md
- research/sprint_004/184_CEX002_STORAGE_SIZING_SOURCE_ACCEPTANCE.md
- research/sprint_004/185_CEX002_STORAGE_SIZING_INTEGRATION_AND_EXECUTION.md
- research/sprint_004/186_CEX002_STORAGE_SIZING_FOCUSED_TEST_FAILURE_REVIEW.md
- research/sprint_004/187_CEX002_STORAGE_SIZING_TEST_SOURCE_ACCEPTANCE.md
- research/sprint_004/188_CEX002_STORAGE_SIZING_RESTART_AND_EXECUTION.md
- research/sprint_004/189_CEX002_STORAGE_SIZING_SECOND_FOCUSED_TEST_FAILURE_REVIEW.md
- research/sprint_004/190_CEX002_STORAGE_SIZING_SPARK_TEST_SOURCE_REVIEW.md
- research/sprint_004/191_CEX002_STORAGE_SIZING_FINAL_TEST_SOURCE_ACCEPTANCE.md
- research/sprint_004/192_CEX002_STORAGE_SIZING_FINAL_RESTART_AND_EXECUTION.md
- research/sprint_004/193_CEX002_STORAGE_SIZING_RUFF_FAILURE_REVIEW.md
- research/sprint_004/194_CEX002_STORAGE_SIZING_RUFF_SOURCE_ACCEPTANCE.md
- research/sprint_004/195_CEX002_STORAGE_SIZING_VERIFICATION_AND_EXECUTION.md
- docs/adr/0022-path-bound-retained-checksum-recovery.md
- docs/adr/0023-retained-credit-separate-from-manifest-consumability.md
- research/sprint_004/196_CEX002_SIZING_AUTHORITY_FAILURE_ARCHITECTURE.md
- research/sprint_004/197_CEX002_PATH_BOUND_RECOVERY_SOURCE_REVIEW.md
- research/sprint_004/198_CEX002_PATH_BOUND_RECOVERY_CORRECTION_REVIEW.md
- research/sprint_004/199_CEX002_PATH_BOUND_RECOVERY_RESIDUAL_REVIEW.md
- research/sprint_004/200_CEX002_PATH_BOUND_RECOVERY_FINAL_RESIDUAL_REVIEW.md
- research/sprint_004/201_CEX002_PATH_BOUND_SOURCE_ACCEPTANCE_TEST_RESIDUAL.md
- research/sprint_004/202_CEX002_PATH_BOUND_TEST_ASSERTION_REVIEW.md
- research/sprint_004/203_CEX002_PATH_BOUND_SOURCE_TEST_ACCEPTANCE.md
- research/sprint_004/204_CEX002_PATH_BOUND_RECOVERY_INTEGRATION.md
- research/sprint_004/205_CEX002_MIGRATION_FIXTURE_FAILURE_REVIEW.md
- research/sprint_004/206_CEX002_MIGRATION_FIXTURE_SOURCE_ACCEPTANCE.md
- research/sprint_004/207_CEX002_MIGRATION_FIXTURE_REINTEGRATION.md
- research/sprint_004/208_CEX002_PATH_BOUND_INTEGRATION_ACCEPTANCE_AND_TRANSITION_DESIGN.md
- research/sprint_004/209_CEX002_PATH_BOUND_TRANSITION_SOURCE_REVIEW.md
- research/sprint_004/210_CEX002_PATH_BOUND_TRANSITION_RESUME_REVIEW.md
- research/sprint_004/211_CEX002_PATH_BOUND_TRANSITION_PREFLIGHT_REVIEW.md
- research/sprint_004/212_CEX002_TRANSITION_FOCUSED_TEST_FAILURE.md
- research/sprint_004/213_CEX002_TRANSITION_SOURCE_TEST_ACCEPTANCE.md
- research/sprint_004/214_CEX002_TRANSITION_INTEGRATION.md
- research/sprint_004/215_CEX002_TRANSITION_INTEGRATION_ACCEPTANCE_AND_EXECUTION.md
- research/sprint_004/216_CEX002_PATH_BOUND_TRANSITION_EXECUTION.md
- research/sprint_004/217_CEX002_PATH_BOUND_QUALIFICATION_AUTHORIZATION.md
- research/sprint_004/218_CEX002_PATH_BOUND_QUALIFICATION_EXECUTION.md
- research/sprint_004/219_CEX002_CORRECTED_SIZING_AUTHORITY_SOURCE_REVIEW.md
- research/sprint_004/220_CEX002_SIZING_CORRECTION_FOCUSED_FAILURE.md
- research/sprint_004/221_CEX002_REAL_AUTHORITY_DECOMPOSITION_REVIEW.md
- research/sprint_004/222_CEX002_SIZING_SOURCE_ACCEPTANCE_AND_EXECUTION.md
- research/sprint_004/223_CEX002_SIZING_INTEGRATION_AND_EXECUTION.md
- research/sprint_004/224_CEX002_COINALYZE_PROVENANCE_CORRECTION.md
- research/sprint_004/225_CEX002_COINALYZE_PROVENANCE_SOURCE_ACCEPTANCE.md
- research/sprint_004/226_CEX002_CORRECTED_SIZING_EXECUTION.md
- research/sprint_004/227_CEX002_COINALYZE_IDENTITY_NAMESPACE_CORRECTION.md
- research/sprint_004/228_CEX002_IDENTITY_SOURCE_ACCEPTANCE_AND_SIZING_RETRY.md
- research/sprint_004/229_CEX002_IDENTITY_CORRECTED_SIZING_EXECUTION.md
- docs/adr/0024-typed-normalization-and-partition-atomic-publication.md
- research/sprint_004/230_CEX002_STORAGE_ARCHITECTURE_CORRECTION.md
- research/sprint_004/232_CEX002_TYPED_SIZING_SOURCE_REVIEW.md
- docs/adr/0025-complete-product-sizing-and-fee-authority.md
- research/sprint_004/233_CEX002_TYPED_SIZING_CORRECTION_REVIEW.md
- docs/adr/0026-non-backdated-fee-scenarios.md
- research/sprint_004/234_CEX002_FEE_AUTHORITY_AND_FINAL_SIZING_CORRECTION.md
- research/sprint_004/235_CEX002_CLAUDE_SIZING_REASSIGNMENT.md
- research/sprint_004/236_CEX002_CLAUDE_COMPLETE_SIZING_DROP_REVIEW.md
- research/sprint_004/237_CEX002_SOL_FINAL_SIZING_CORRECTION.md
- research/sprint_004/238_CEX002_RETAINED_LINEAGE_AUTHORITY_CORRECTION.md
- research/sprint_004/239_CEX002_V2_SIZING_SOURCE_ACCEPTANCE_AND_EXECUTION.md
- research/sprint_004/240_CEX002_V2_SIZING_INTEGRATION_AND_EXECUTION.md
- research/sprint_004/241_CEX002_V2_SIZING_VALIDATION_FAILURE_REVIEW.md
- research/sprint_004/242_CEX002_V2_SIZING_CORRECTION_ACCEPTANCE_AND_EXECUTION.md
- research/sprint_004/243_CEX002_V2_SIZING_CORRECTION_INTEGRATION_AND_EXECUTION.md
- research/sprint_004/244_CEX002_V2_SIZING_IDEMPOTENCE_FAILURE_REVIEW.md
- research/sprint_004/245_CEX002_V2_STABLE_CAPACITY_RESIDUAL_REVIEW.md
- research/sprint_004/246_CEX002_V2_SIZING_IDEMPOTENCE_ACCEPTANCE_AND_EXECUTION.md
- research/sprint_004/247_CEX002_V2_SIZING_IDEMPOTENCE_INTEGRATION_AND_EXECUTION.md
- research/sprint_004/248_CEX002_V2_RECEIPT_BOUNDARY_AND_COMPONENT_IDENTITY_REVIEW.md
- research/sprint_004/249_CEX002_V2_RECEIPT_BOUNDARY_ACCEPTANCE_AND_EXECUTION.md
- research/sprint_004/250_CEX002_V2_SIZING_FINAL_INTEGRATION_AND_EXECUTION.md
- research/sprint_004/251_CEX002_REAL_TYPED_SOURCE_SEMANTICS_REVIEW.md
- research/sprint_004/252_CEX002_TYPED_SOURCE_IMPLEMENTATION_ROUTING.md
- research/sprint_004/253_CEX002_TYPED_SOURCE_TEST_RESIDUAL_REVIEW.md
- research/sprint_004/254_CEX002_CLAUDE_TYPED_SOURCE_TEST_CORRECTION.md
- research/sprint_004/255_CEX002_REAL_TYPED_SOURCE_ACCEPTANCE_AND_EXECUTION.md
- research/sprint_004/256_CEX002_V2_SIZING_TYPED_SOURCE_INTEGRATION_AND_EXECUTION.md
- docs/adr/0027-partition-aware-dictionary-storage-sizing.md
- docs/adr/0028-immutable-sizing-basis-and-renewable-capacity-attestation.md
- research/sprint_004/257_CEX002_V2_CAPACITY_MODEL_REJECTION_AND_V3_ARCHITECTURE.md
- research/sprint_004/259_CEX002_V3_DICTIONARY_SOURCE_RESIDUAL_REVIEW.md
- research/sprint_004/260_CEX002_V3_COMPLETE_ALLOCATION_RESIDUAL_REVIEW.md
- research/sprint_004/261_CEX002_V3_DISJOINT_LAYOUT_FINAL_SOURCE_REVIEW.md
- research/sprint_004/262_CEX002_V3_LITERAL_ALLOCATION_CORRECTION.md
- research/sprint_004/263_CEX002_V3_MEASURED_IDENTITY_ANCHOR_COMPLETION.md
- research/sprint_004/264_CEX002_V3_MEASURED_ANCHOR_TEST_RESIDUAL.md
- research/sprint_004/265_CEX002_V3_SOURCE_ACCEPTANCE_AND_EXECUTION.md
- research/sprint_004/266_CEX002_V3_SIZING_INTEGRATION_AND_EXECUTION.md
- research/sprint_004/267_CEX002_V3_FOCUSED_TEST_FAILURE_REVIEW.md
- research/sprint_004/268_CEX002_V3_SPARK_TEST_RESIDUAL.md
- research/sprint_004/269_CEX002_V3_SPARK_CONTINUATION_REJECTION.md
- research/sprint_004/270_CEX002_V3_SENIOR_AVAILABILITY_REROUTE.md
- research/sprint_004/271_CEX002_V3_TEST_SOURCE_ACCEPTANCE_AND_EXECUTION.md
- research/sprint_004/272_CEX002_V3_CORRECTED_SIZING_EXECUTION.md
- research/sprint_004/273_CEX002_V3_CAPACITY_TEST_ORDERING_FAILURE.md
- research/sprint_004/274_CEX002_TARGETED_SENIOR_TEST_AUTHORIZATION.md
- research/sprint_004/275_CEX002_REVIEWER_TARGETED_TEST_AUTHORIZATION.md
- research/sprint_004/276_CEX002_V3_ORDERING_SOURCE_ACCEPTANCE_AND_EXECUTION.md
- research/sprint_004/277_CEX002_V3_ORDERING_INTEGRATION_AND_EXECUTION.md
- research/sprint_004/278_CEX002_V3_BLOCKED_MEASUREMENT_AND_CAPACITY_ATTESTATION_ARCHITECTURE.md
- research/sprint_004/279_CEX002_CAPACITY_ATTESTATION_SOURCE_REVIEW.md
- research/sprint_004/280_CEX002_CAPACITY_ATTESTATION_RESIDUAL_REVIEW.md
- research/sprint_004/281_CEX002_CAPACITY_ATTESTATION_SOURCE_ACCEPTANCE_AND_EXECUTION.md
- research/sprint_004/284_CEX002_REVIEW281_BASE_PREPROOF_CORRECTION.md
- research/sprint_004/285_CEX002_REVIEW281_LITERAL_PREPROOF_REPAIR.md
- docs/engineering/DEVELOPMENT_ROLES.md

## Decision

Review 265 accepts the v3 source/test drop for exact Hermes integration and execution.
Hermes runs the focused validation, then only on success one real v3 sizing invocation and
one identical idempotence invocation, publishes record 266, commits/pushes only enumerated
paths, and stops for reviewer inspection. No acquisition or later work is authorized.

The destination is the complete real data needed by the original Harmonic Trader
geometry-plus-derivatives thesis before model development. CEX-002 acquires every
historically observed Binance USD-M perpetual and publishes real hourly bars and taker
flow, five-minute OI, funding, basis, observed liquidation flow, bounded real cost evidence,
typed gaps, provenance, reconciliation, resumability, a pinned bundle, and a clean
NautilusTrader catalog-load check.

No fixed-N/current-listing universe, synthetic acceptance artifact, zero-filled missing
data, silent partial success, paid data purchase, historical-full-L2 prerequisite, DEX
work, harmonic-model development, payoff analysis, PAPER, or LIVE work is authorized.

## Why this reaches the target without Tardis

Official Binance archives/APIs supply native hourly bars with total/taker-buy volumes,
five-minute OI/metrics, realized funding, and hourly mark/index/premium/basis inputs for
free. Coinalyze's free API retains daily long/short liquidation history indefinitely.
Because Binance itself publishes at most the latest liquidation per symbol per second,
this field is explicitly an observed, censored liquidation aggregate; no implementation
may claim event completeness.

The original model needs terminal-leg OI change, funding state, and liquidation imbalance,
not individual trades or a complete historical book. Cost evidence is a frozen
first/midpoint/last per-contract quote/depth sample. Monthly archives are canonical for
completed months and daily objects fill only uncovered dates, so overlapping package
copies are never acquired. Live stream collection is deferred until historical research
establishes tradability.

## Superseded work

- DEX-003 remains `SUPERSEDED`; preserve all its source drops, data, and evidence.
- CEX-001 is `SUPERSEDED`; preserve its rejected source drop without integration.
- The five invalid BitMEX funding artifacts remain preserved and must be quarantined under
  CEX-002 Gate 0 before any research consumer can resolve them.

## Spark source review

Spark delivered a final four-path drop at the exact hashes recorded in review 61. Source
inspection rejects it before Jr integration. Direct probes prove headerless numeric data
is still accepted as a schema and tampered content-addressed bytes are trusted on resume.
The Coinalyze client is fabricated receipt plumbing over nonexistent endpoints rather than
a real source client, S3 pagination remains invalid, an unproved 64 MiB cap remains, and
the matrix can both silently promote partial sources and remain permanently blocked by
derived outputs. Exact findings are in review 61.

The earlier transient write under the preserved CEX-001 paths is a provenance breach. The
final reviewed drop is now in the authorized non-colliding paths, but the original rejected
CEX-001 source bytes recorded in review 59 are no longer present at those old paths. Do not
claim they were preserved or restored.

## Review-publication transition

If committed `HEAD` does not yet contain review 61 plus the Grok designation in both this
file and `tickets/CEX-002.md`, Jr Dev — Hermes must publish only:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/61_CEX002_SPARK_SOURCE_REVIEW.md`; and
- `tickets/CEX-002.md`.

Jr runs only `python3 scripts/check_repo_control.py` and `git diff --check`, excludes every
source/test drop and unrelated dirty path, pushes, and establishes `HEAD == origin/main`.
Once the committed branch contains all three records, the Grok authorization below becomes
active automatically; no further handoff edit or owner-supplied source hash is required.

## Grok corrective source authorization

Sr Dev — Grok Build, using Grok 4.6 High, may replace only the final reviewed CEX-002
source/test paths and fixture directory recorded in review 61. The correction must close
all fifteen findings in that record, including:

- real Coinalyze history endpoints, query contract, response parsing, source samples,
  retention/unit evidence, overlap-reconciliation inputs, and environment-only secret use;
- correct S3 ListObjectsV2 pagination and exact one-minute interval selection;
- known per-family header/headerless schemas backed by real-shaped fixtures;
- checksum-required, rehashed resume with no unproved object-size cap;
- complete-family/symbol/incident-aware authority with no quote-label promotion;
- source-gate treatment that does not block on derived outputs;
- available `bookDepth` plus `bookTicker` cost inventory;
- authenticated current-contract comparison and explicit historical-perpetual rule; and
- nonzero default exit for incomplete required source coverage.

Grok authors source and test source only. It performs no network run, test execution,
integration, repository-record edit, Git operation, commit, push, purchase, catalog
mutation, or publication and stops for fresh reviewer source inspection with exact hashes.
Jr integration remains unauthorized.

## First Grok corrective source review

Grok's rewrite closes most review-61 defects, but source inspection rejects three residual
source-authority failures at the exact hashes in review 63. The supplied headerless metrics
fixture is still classified as field names; aggregate family counts still promote a product
to official completeness when a discovered symbol has zero objects; and Coinalyze can
qualify BTC responses for an ETH-only request while reporting a schema path instead of the
actual liquidation/OI unit. The bounded real Coinalyze responses also need redacted content
hash/retrieval provenance in the qualification evidence.

Grok executed tests despite the explicit role prohibition. Those results are disregarded;
Hermes remains the only integration and command-execution actor.

## Second Grok correction authorization

If committed `HEAD` does not yet contain review 63 plus this section and the matching
ticket section, Jr Dev — Hermes must first publish only:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/63_CEX002_GROK_SOURCE_REVIEW.md`; and
- `tickets/CEX-002.md`.

Jr runs only `python3 scripts/check_repo_control.py` and `git diff --check`, excludes all
source/test drops and unrelated dirty paths, pushes, and establishes
`HEAD == origin/main`. Once that committed branch state exists, Sr Dev — Grok Build on
Grok 4.6 High is automatically authorized for the surgical correction in review 63; no
ephemeral prompt, owner-supplied source hashes, or further handoff edit is required.

The correction is confined to the three reviewed Python paths and existing fixture
directory. It must preserve the accepted rewrite, add failing-then-passing focused tests
for the three direct probes, and add redacted Coinalyze response provenance. Grok performs
no test execution, network run, integration, record edit, Git operation, commit, push,
purchase, catalog mutation, or publication. It stops for source review with exact hashes.
Jr integration remains unauthorized.

## Second Grok corrective source review

The second Grok patch closes metrics schema identity, Coinalyze requested/returned symbol
checking, actual unit reporting, and empty listed-prefix detection. Review 64 rejects two
remaining semantic defects and one test-source defect: a universe symbol absent from a
product family is still omitted and can be silently promoted; reported Coinalyze
provenance hashes reconstructed JSON rather than retained raw responses; and the new
mismatch test expects a different error from the correct implemented failure.

Grok 4.6 High has now required two rejected corrective reviews on this source-authority
task. The next bounded correction is routed to Sr Dev — Claude Build using Claude Opus 5.

## Claude review-publication transition

If committed `HEAD` does not yet contain review 64, the Claude senior-role addition, this
section, and the matching ticket section, Jr Dev — Hermes must first publish only:

- `AGENTS.md`;
- `docs/engineering/DEVELOPMENT_ROLES.md`;
- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/64_CEX002_GROK_SECOND_SOURCE_REVIEW.md`; and
- `tickets/CEX-002.md`.

Jr runs only `python3 scripts/check_repo_control.py` and `git diff --check`, excludes all
source/test drops and unrelated dirty paths, pushes, and establishes
`HEAD == origin/main`. Once that committed state exists, Sr Dev — Claude Build on Claude
Opus 5 is automatically authorized for the surgical correction in review 64; no ephemeral
prompt, owner-supplied source hashes, or further handoff edit is required.

## Claude corrective source acceptance

Review 65 accepts Claude's source-only correction at exact hashes. Full-universe missing
family prefixes now become typed blocking evidence; Coinalyze provenance now identifies
and rehashes retained raw response bytes; and the focused mismatch test contract is
correct. This is the first accepted Claude Build source review and is positive
project-specific routing evidence, pending Hermes integration.

Jr Dev — Hermes is authorized to perform only the integration, command sequence, two real
Gate 1 qualification/resume runs, evidence record, commit, and push specified verbatim in
review 65. The key must be loaded only from `.env` into `COINALYZE_API_KEY`, never printed
or placed in command arguments. Exit 2 is preserved as honest blocked-matrix evidence, not
reported as success. Exit 1 stops the run. Interrupted work resumes the same store and
progress file. The execution record path is
`research/sprint_004/66_CEX002_GATE1_EXECUTION.md`.

For this intermediate Gate 1 integration, Hermes runs the focused CEX-002 suite and the
directly depended-on atomic-download suite specified in review 65. The already attempted
full-suite failures in excluded dirty DEX/BitMEX drops are recorded as nonblocking
environmental evidence. No `-k` substitute or clean-worktree rerun is authorized. The
unchanged full suite remains mandatory once at final CEX-002 release acceptance.

## Claude operational-correction source review

Claude's first review-67 correction is rejected at the exact hashes in review 68. The
patch establishes the right architecture, but direct probes prove that cross-request
listing-page substitution and mismatched provider-checksum checkpoints are accepted,
malformed checkpoints silently restart empty, and the preflight budget counts one unique
object multiple times across regime aliases. Retry incidents are not durable across an
abort, retry ownership can nest, and the required abort/resume test is absent. Jr
integration and another real run remain unauthorized.

Hermes must first publish only this file, review 68, and `tickets/CEX-002.md`, excluding
the rejected source/test drop and every unrelated dirty path. Once that record is committed
and pushed, Sr Dev — Claude Build on Claude Opus 5 is automatically authorized for the
surgical correction in review 68. No ephemeral developer prompt is required.

## Gate 1 real-execution review

Review 75 accepts Hermes's integration discipline but rejects Gate 1 evidence. Both real
runs honestly blocked and the store resumed, but the archive-name union was promoted into
an unproved perpetual universe, the 256 MiB allowance reset across invocations, semantic
sample identity changed, source qualification was conflated with temporal completeness,
and the report exposed a multi-terabyte raw requirement without a deduplicated physical
storage/shortfall decision.

Sr Dev — Claude Build using Claude Opus 5 is authorized only for the source/test correction
specified in review 75. It must establish affirmative official membership evidence,
immutable cumulative planning, physical storage feasibility evidence, separated source and
coverage states, and stable Coinalyze anchors. It performs no tests, network/data run,
integration, records, Git, purchase, deletion, catalog mutation, Gate 2, or Harmonic Trader
work and stops for source review with exact hashes. Hermes and every real rerun remain
unauthorized.

## Claude review-75 source review

Review 76 rejects Claude's first review-75 correction while retaining its membership,
coverage-state, Coinalyze-anchor, physical-storage, plan-lock, and cumulative-ledger
direction. The residual blockers are a crash window between sample checkpoint and ledger
write, unauthenticated retained FAPI rows, unstable/incomplete plan input identities,
unverified storage credit, unsupported temporal-gap explanations, and truncated Coinalyze
product gaps.

Sr Dev — Claude Build using Claude Opus 5 is authorized only for the surgical nine-path
source/test/fixture correction in review 76. It performs no tests, network/data run,
integration, records, Git, purchase, deletion, catalog mutation, Gate 2, Nautilus, or
Harmonic Trader work and stops for source review with exact hashes. Hermes remains
unauthorized.

## Claude review-76 source review

Review 77 accepts the crash-safe reservation, legacy range, plan-validation, storage,
temporal-gap, and complete-gap closures but rejects the source before integration. The
remaining failures are confined to raw/parsed exchangeInfo binding and value validation,
full re-proved plan authority inputs, persisted-ledger validation, and native identity for
the complete Coinalyze support map.

Sr Dev — Claude Build using Claude Opus 5 is authorized only for the final two-path source
and test-source correction in review 77. It performs no tests, network/data run,
integration, fixtures, records, Git, purchase, deletion, catalog mutation, Gate 2,
Nautilus, or Harmonic Trader work and stops for source review with exact hashes. Hermes
remains unauthorized.

## Claude review-77 source review

Review 78 accepts inseparable raw exchangeInfo parsing, re-proved listing/retained plan
inputs, and full Coinalyze native identity. The source still cannot resume live because
volatile response SHA/server time are plan inputs; unknown nonempty contract semantics can
qualify; and reduced positive or zero persisted ledger amounts restore allowance.

Sr Dev — Claude Build using Claude Opus 5 is authorized only for the two-path correction
in review 78. It performs no tests, network/data run, integration, fixtures, records, Git,
purchase, deletion, catalog mutation, Gate 2, Nautilus, or Harmonic Trader work and stops
for source review with exact hashes. Hermes remains unauthorized.

## Claude review-78 source review

Review 79 accepts the stable semantic/provenance split, fail-closed contract semantics,
and structured ledger direction, but rejects two residual transition defects. A changed
live authority response is durably written before the immutable plan rejects it and can
poison later valid resumes. The in-memory acquisition path fetches a raw payload before
declaring a content-address reuse, then records the transfer as zero-byte no-transfer.

At the owner's direction, Sr Dev — Grok Build using Grok 4.6 High is authorized only for
the two-path correction in review 79 because Claude is unavailable. Grok performs no
tests, network/data run, integration, fixtures, records, Git, purchase, deletion, catalog
mutation, Gate 2, Nautilus, or Harmonic Trader work and stops for source review with exact
hashes. Hermes remains unauthorized.

## Grok review-79 source review

Review 80 accepts Grok's two-path correction. Live authority and first-closed evidence are
now staged until the immutable plan accepts them, so a rejected response cannot poison
durable metadata. Content-address reuse is proved before raw retrieval; an actual raw
fetch is always recorded as transferred. Focused source tests cover both corrections.

Hermes is authorized only for the nine-path accumulated CEX-002 integration, focused
commands, preserved-store two-run qualification/resume, evidence record 81, commit, and
push specified in review 80. Exit 2 remains honest blocked evidence, not success. Exit 1
stops further network work. The full suite remains deferred to final release acceptance.

## Focused integration failure review

Review 82 accepts Hermes's stop and retains review 80's production acceptance. All five
failures are stale or internally inconsistent test contracts: current-unarchived gap
precedence, typed temporal coverage, an incomplete oversized-source fixture, immutable
plan history, and a row-validation test missing its authenticated envelope.

Codex Spark is authorized only for the one-path mechanical test-source correction in
review 82. It performs no tests, production/fixture edit, integration, records, Git,
network/data run, Gate 2, Nautilus, or Harmonic Trader work and stops for source review
with the exact test hash. Hermes remains unauthorized.

## First Spark test-source review

Review 83 accepts three corrections but rejects two residual test defects. The oversized
fixture still lacks affirmative current-perpetual membership, and the immutable-plan test
retains the same rewritten retained/new byte expectations that originally failed.

Spark is authorized only for the two exact one-file test corrections in review 83. It
performs no tests, production/fixture edit, integration, records, Git, network/data run,
Gate 2, Nautilus, or Harmonic Trader work and stops for review with the exact test hash.
Hermes remains unauthorized.

## Final Spark test-source review

Review 84 accepts Spark's one-file correction. All five stale focused tests now express
the accepted current-unarchived, typed-coverage, complete-fixture, immutable-plan, and
authenticated-envelope contracts, and the intermediate unused assignment is removed.

Hermes is authorized only for the nine-path integration, full focused command sequence,
preserved-store two-run qualification/resume, evidence record 85, commit, and push
specified in review 84. Exit 2 remains honest blocked evidence; exit 1 stops network work.
Gate 2, Nautilus, and model work remain unauthorized.

## Focused lint failure review

Review 86 accepts Hermes's stop but supersedes review 84's test acceptance. The 51 unused
imports are evidence that Spark overwrote the accumulated roughly 3,600-line suite with a
correction based on the older committed test file, deleting the review-75 through
review-79 coverage. The passing 84-case result is therefore incomplete. Production
acceptance remains unchanged.

Grok is authorized only to restore the deleted test sections in the single test path from
the governing reviews. It performs no tests, production/fixture edit, integration,
records, Git, network/data run, Gate 2, Nautilus, or Harmonic Trader work and stops for
review with the exact hash and test-function count. Hermes remains unauthorized.

## Stop condition

The only active authorization is Hermes's command and real execution in review 87. The
accepted nine-path drop is committed. The existing store, legacy plan, checkpoints,
reports, and over-budget retained
evidence must be preserved. CEX-002 remains `IN_PROGRESS`; Gate 2, every other ticket,
Nautilus integration, and model work remain unauthorized; next ticket remains `NONE`.

## Grok restored test-source review

Review 87 accepts the restored 3,669-line, 135-function test source. Every deleted
review-75 through review-79 section is present, Spark's five corrections remain, and no
duplicate test names were found. Production acceptance is unchanged.

At the owner's explicit direction, the reviewer commits and pushes the exact accepted
nine-path drop with review 87. Hermes then runs only the focused commands and
preserved-store execution. Failures are corrected forward; no restore, reset, checkout,
stash, clean, or discard is authorized. Gate 2, Nautilus, and model work remain
unauthorized.

## Gate 1 stable-authority execution review

Review 89 accepts Hermes's integration and stop discipline but rejects Gate 1 evidence.
The required semantic identity assertion failed because a volatile local-storage
shortfall was duplicated into an identity-bearing incident note. The real Coinalyze
market map also exposed an unsupported native naming form: `AAVEUSD_PERP` correctly maps
to `AAVEUSD_PERP.A`, not `AAVEUSD_PERP_PERP.A`.

Sr Dev - Grok Build using Grok 4.6 High is authorized only for the two production/test
paths and exact corrections in review 89. It performs no tests, network/data run,
integration, records, Git, purchase, deletion, catalog mutation, Gate 2, Nautilus, or
Harmonic Trader work and stops for reviewer inspection with exact hashes. The 63
unresolved historical candidates and approximately 8.47 TB local shortfall remain honest
blockers; no reduced universe, omitted derivatives data, or price-only substitute is
authorized. Hermes remains unauthorized.

## Grok review-89 source review

Review 90 accepts Grok's exact two-path correction. The storage incident is stable while
exact capacity values remain reported, and already-suffixed Coinalyze native identities
map without duplicating `_PERP`. Full-market mismatch and duplicate validation remains
fail-closed. The accumulated test suite remains intact with four focused additions.

At the owner's standing direction, the reviewer integrates this small accepted drop with
review 90. Hermes then executes only the focused commands and preserved-store two-run
sequence in review 90, records both actual process exit statuses, publishes record 91,
commits the exact authorized four record/report paths, pushes, and stops for review. Gate
2, Nautilus, other tickets, and Harmonic Trader work remain unauthorized.

## Plan-version gate review

Review 92 accepts Hermes's 148 focused tests, 11 atomic-download tests, lint/control
checks, captured exit 1, and required stop. The accepted code hash correctly moved the
immutable code/config input. Review 92 corrects record 91's plan counts and authorizes one
assertion-bound migration from plan version 1 to version 2 with the exact plan, retained
snapshot, budget snapshot, and plan digest preserved; only the reviewed code/config digest
changes and version 1 remains in history.

Hermes executes only review 92's exact migration and two preserved-store runs, publishes
record 93, commits the authorized record/report paths, pushes, and stops for review. No
public relock switch, plan reselection, acquisition, Gate 2, Nautilus, other ticket, or
Harmonic Trader work is authorized.

## Plan-version migration review

Review 94 accepts Hermes's required stop. All pre-migration assertions passed, but the
in-memory exact-plan assertion exposed that `SamplePlan.to_dict()` emits tuple-valued
`products` while persisted JSON reloads lists. The durable lock was never flushed and
remains byte-identical version 1.

Grok is authorized only for review 94's two-path JSON-native plan serialization and
focused test-source correction. Grok performs no tests, data/network run, integration,
records, Git, migration, Gate 2, Nautilus, other-ticket work, or Harmonic Trader work and
stops for reviewer inspection with exact hashes. Hermes remains unauthorized.

## Grok review-94 source review

Review 95 accepts the two-path correction. Plan entries now serialize `products` as
JSON-native lists while retaining internal tuples, and the focused test binds exact JSON
round-trip and unchanged plan digest. The accumulated suite remains intact.

At the owner's standing direction, the reviewer integrates the accepted correction and
review 95. Hermes then runs the focused commands, exact assertion-bound plan-2 migration,
and preserved-store two-run sequence in review 95, publishes record 96, commits the exact
authorized report/record paths, pushes, and stops for review. Gate 2, Nautilus, other
tickets, and Harmonic Trader work remain unauthorized.

## Gate 1 plan-2 execution review

Review 97 accepts the reproducible execution evidence but does not pass Gate 1. Both real
runs captured exit 2, Coinalyze qualified, the plan migration preserved immutable history,
and semantic resume identity passed. No further developer correction is authorized.

CEX-002 is blocked by 63 archive-only names without affirmative official historical
membership authority and by 8,661,196,012,122 projected new raw bytes against only
185,976,057,856 available local bytes; normalized/catalog storage is additionally unknown.
The Owner may supply storage and exact official source artifacts but is not an acceptance
authority. No reduced universe, omitted derivatives fields, discarded required raw
provenance, price-only substitute, Gate 2, Nautilus, other ticket, or Harmonic Trader work
is authorized. Next ticket remains `NONE`.

## Resolution and storage architecture correction

Review 98 preserves review 97's execution facts but rejects its storage disposition. The
8.66 TB inventory came from reviewer-authored scope inflation: historical `trades` plus
`aggTrades`, full book archives, one-minute data, and overlapping daily/monthly packages.
Those are not requirements of the reviewed Harmonic model or data contract.

ADR-0017 and CEX-002 now require native hourly bars and bar-derived taker flow, native
five-minute OI, funding, hourly basis inputs, observed daily liquidations, and a bounded
first/midpoint/last per-contract cost sample across available book families. The complete
historical perpetual universe, derivatives variables, raw lineage, typed gaps, and daily
model intersection remain mandatory. This is not a price-only or fixed-panel reduction.

Sr Dev - Grok Build using Grok 4.6 High is authorized only for review 98's four-path
source/test correction. It performs no tests, network/data run, plan migration, integration,
records, Git, bulk acquisition, catalog mutation, Nautilus work, or Harmonic Trader work and
stops for reviewer inspection with exact hashes. Hermes remains unauthorized. Gate 1 is
`IN_PROGRESS`; Gate 2 and every next ticket remain unauthorized; next ticket is `NONE`.

## Grok review-98 source outcome - rejected

Review 99 preserves Grok's corrected one-hour product/family scope, bounded cost-sample
direction, explicit unknown later storage fields, and nonblocking Coinalyze intersection
gaps, but rejects the drop before integration. The existing execution path either rejects
or replays the locked old plan, while a fresh store writes and executes a version-1 plan;
the report then mislabels that same plan as an unmigrated version-3 candidate. The new
allowance is not separately ledgered, selected manifest identities and intervals are not
serialized or integrity-qualified, taker-flow availability is not connected to production
coverage, total-unknown storage can still print Gate 2 `sufficient`, and no actual holdout
boundary is pinned. One new collision test also cannot reach its asserted branch.

Sr Dev - Claude Build using Claude Opus 5 is authorized only for review 99's bounded
three-path source/test correction and optional focused fixtures. Claude preserves every
accepted direction, reads the durable version-2 lock and legacy ledger without mutation,
emits a distinct inspectable version-3 candidate under a separate amendment-ledger
identity, performs no raw sample acquisition, and adds the exact focused test contracts in
review 99. Claude performs no tests, network/data run, migration, integration, repository
records, Git, catalog work, Nautilus work, or Harmonic Trader work and stops for reviewer
inspection with exact hashes and the test-function count. Hermes remains unauthorized.
Gate 1 remains `IN_PROGRESS`; Gate 2 and every next ticket remain unauthorized; next ticket
is `NONE`.

## Claude review-99 source outcome - rejected

Review 100 accepts Claude's separate candidate-mode structure, no-acquisition loop,
inspectable interval manifest, Gate-2 unknown state, durable holdout, fixed collision test,
and preservation of the 160-function accumulated suite. Integration remains unauthorized
for four control defects: candidate mode can reconcile and flush the legacy ledger before
taking its before hash; candidate-mode taker flow ignores re-proved retained schema
evidence because its `samples` collection is intentionally empty; the reported candidate
plan digest uses an identity domain that cannot become the future locked-plan digest; and
the prior-authority check accepts version 3 or later instead of exact version 2 with
versions 0 and 1 preserved. Manifest rows also conflate a listed checksum-sidecar path with
proved consumable integrity.

Sr Dev - Claude Build using Claude Opus 5 is authorized only for review 100's surgical
three-path correction and optional bounded checksum fixture. Claude removes all legacy
reconciliation from candidate mode, proves an outstanding reservation cannot mutate,
derives taker flow from retained schema without download, restores a comparable round-trip
plan digest, requires exact version-0-through-2 authority, and makes manifest validation
states honest. Claude performs no tests, network/data run, migration, integration,
repository records, Git, acquisition, catalog work, Nautilus work, or Harmonic Trader work
and stops for reviewer inspection with exact hashes and the test-function count. Hermes
remains unauthorized. Gate 1 remains `IN_PROGRESS`; Gate 2 and every next ticket remain
unauthorized; next ticket is `NONE`.

## Claude review-100 source outcome - rejected

Review 101 accepts the read-only legacy ledger branch, retained-schema taker-flow evidence,
round-trippable plan-content digest, separate candidate-envelope digest, honest manifest
validation states, and preservation of the 166-function accumulated suite. Integration
remains unauthorized because exact prior authority is checked only after inventory/cache
work and a durable holdout write, so an invalid version or history can mutate candidate
state before rejection. The history parser also coerces a missing version to version 0,
accepts reversed version-1/version-0 order, and does not parse or structurally validate the
preserved version-0 plan. Its empty recorded digest is discarded instead of deriving a
comparable content identity.

Sr Dev - Claude Build using Claude Opus 5 is authorized only for review 101's final
production/test correction. Claude moves exact read-only authority preflight ahead of every
candidate write or remote/cache operation, requires ordered and strictly typed history
versions `[0, 1]`, parses and structurally validates both historical plan documents under
their version-appropriate contracts, and includes a deterministic derived version-0 plan
content identity in reuse comparison without rewriting the lock. Claude performs no tests,
network/data run, migration, integration, repository records, Git, acquisition, catalog
work, Nautilus work, or Harmonic Trader work and stops for reviewer inspection with exact
hashes and the test-function count. Hermes remains unauthorized. Gate 1 remains
`IN_PROGRESS`; Gate 2 and every next ticket remain unauthorized; next ticket is `NONE`.

## Claude review-101 source outcome - CLI boundary rejected

Review 102 accepts the production preflight, strict ordered lineage, derived version-0
identity, reusable authority objects, final lock/ledger rehash, and intact 168-function
test source. The production and fixture hashes are frozen. Hermes remains unauthorized
because the executable CLI creates the store and loads/bootstraps listing and retry state
before it calls the safe production function. An invalid `--candidate-plan-only` request
can therefore mutate through the real entry point before production preflight rejects it.
Review 101 incorrectly froze that CLI while demanding process-wide preflight; this is a
reviewer scope error, not a failure to implement the authorized two-path correction.

Sr Dev - Claude Build using Claude Opus 5 is authorized only to move a read-only
`candidate_preflight` call in front of every CLI-side directory, transport, cache,
checkpoint, journal, listing, current-contract, and Coinalyze operation and to add one
focused CLI test proving invalid authority returns exit 1 without any store-tree or remote
facility mutation. Only the CLI and CEX-002 test path may change. Claude performs no tests,
network/data run, migration, integration, repository records, Git, acquisition, catalog
work, Nautilus work, or Harmonic Trader work and stops for reviewer inspection with exact
hashes and the test-function count. Hermes remains unauthorized. Gate 1 remains
`IN_PROGRESS`; Gate 2 and every next ticket remain unauthorized; next ticket is `NONE`.

## Claude review-102 source outcome - accepted for integration

Review 103 accepts the accumulated three-path CEX-002 source/test drop. The real CLI now
preflights exact candidate authority before credential access, directory creation, or any
transport/cache/checkpoint/journal setup; production repeats the read-only validation and
keeps the durable version-2 lock and legacy ledger byte-immutable. The focused CLI test
invokes `main`, blocks every downstream facility, snapshots files and directories, verifies
exit 1, and proves secret redaction. The production hash and fixtures remain unchanged and
the accumulated suite contains 170 uniquely named test functions.

Jr Dev - Hermes is authorized only for review 103's exact three-path integration, focused
commands, and one real `--candidate-plan-only` run against the preserved store. It records
the result in review 104, including exact before/after lock, ledger, raw-tree, amendment,
report, plan, manifest, storage, membership, and source evidence. No plan migration, sample
download, amendment-ledger creation, Gate 2, normalization, catalog work, Nautilus work,
Harmonic Trader work, or other-ticket work is authorized. A command failure or real exit 1
stops forward execution and is recorded honestly. Gate 1 remains `IN_PROGRESS`; next ticket
remains `NONE`.

## Review-104 focused execution outcome - rejected

Review 105 accepts Hermes's exact three-path source integration and confirms that the real
candidate process did not run. The focused CEX-002 suite failed 12 of 189 cases. Five
stable-identity failures expose a real one-invocation lag in the report-facing acquisition
manifest, and retained kline schema proves candidate taker flow while its derived row
incorrectly remains sample-pending. Six other failures are stale or invalid tests built on
discovery-only trade families, trade-shaped kline payloads, or a whole-file substring ban.
Commands 2 through 5 were run after command 1 failed; they were read-only but are void as
acceptance evidence.

Sr Dev - Claude Build using Claude Opus 5 is authorized only for review 105's bounded
production and test correction. The production module must publish final proof state from
current-run re-proof/acquisition evidence without changing the locked plan and must qualify
retained-schema taker flow without hiding real coverage or integrity blocks. The tests must
use selected one-hour kline families and schema-valid distinct kline bytes while preserving
all identity, tamper, resume, transfer, lineage, and zero-fetch guarantees. Only the
production and CEX-002 test paths may change; the CLI and 17 fixtures are frozen.

Claude performs no tests, network/data run, migration, integration, repository-record
edit, Git, acquisition, catalog work, Nautilus work, Harmonic Trader work, or publication
and stops for reviewer inspection with exact hashes and the unique test-function count.
Hermes and real candidate execution remain unauthorized. Gate 1 remains `IN_PROGRESS`;
next ticket remains `NONE`.

## Claude review-105 source outcome - accepted for integration

Review 106 accepts the exact two-path correction after static source review. The final
report-facing manifest is rebuilt from current-run proof without changing the locked plan,
and candidate taker flow removes both the artificial retained-schema sample-pending state
and its matching release block while preserving real budget, coverage, membership, and
integrity blocks. The six stale test contracts now use selected kline inputs,
schema-correct distinct payloads, and exact CLI boundaries. The CLI and 17 fixtures remain
unchanged; the suite retains 170 unique test functions.

Jr Dev - Hermes is authorized only for review 106's exact two-path integration, strict
stop-on-first-failure focused command sequence, and one candidate-only real execution after
all five commands pass. It publishes record 107 with the complete before/after authority,
raw-tree, report, candidate-plan, manifest, storage, membership, and source evidence. No
out-of-band developer instruction is authority; review 106 contains the complete task.

No plan migration, sample acquisition, amendment-ledger creation, Gate 2, normalization,
catalog work, Nautilus work, Harmonic Trader work, or other-ticket work is authorized. A
nonzero focused-command exit stops immediately before every later command and the real
candidate process. Gate 1 remains `IN_PROGRESS`; next ticket remains `NONE`.

## Review-107 focused execution outcome - rejected

Review 108 accepts Hermes's exact two-path integration and strict stop after focused
command 1 failed 3 of 189 cases. Commands 2 through 5 and the real candidate process were
correctly not run. One production defect lets retained proof override the outcome-blind
listed-sidecar prerequisite and reselect an unchecksummed monthly package over its daily
fallback. Two test failures compare independently pinned prospective holdout instants;
those are semantic differences and must be aligned with a common fixed `now`, not hidden
from identity.

Sr Dev - Claude Build using Claude Opus 5 is authorized only for review 108's two-path
correction. It restores listed-sidecar-before-proof integrity precedence and fixes the two
identity tests to pin the same timezone-aware first qualification instant across compared
stores. The CLI, 17 fixtures, final proof rebuild, taker-flow logic, holdout implementation,
identity drop keys, locked plan, ledger behavior, and all other contracts are frozen.

Claude performs no tests, network/data run, migration, integration, repository-record
edit, Git, acquisition, catalog work, Nautilus work, Harmonic Trader work, or publication
and stops for reviewer inspection with exact hashes and the unique test-function count.
Hermes and real candidate execution remain unauthorized. Gate 1 remains `IN_PROGRESS`;
next ticket remains `NONE`.

## Claude review-108 source outcome - accepted for integration

Review 109 accepts the exact two-path residual correction after static source review.
Listed-sidecar eligibility now precedes proof, so proof cannot re-admit an ineligible
monthly object or alter cadence selection. The two cross-root identity tests pin one common
first holdout instant and still compare complete semantic identity while resume replays the
durable boundary. The CLI and 17 fixtures remain unchanged; the suite retains 170 unique
test functions.

Jr Dev - Hermes is authorized only for review 109's exact two-path integration, strict
stop-on-first-failure focused sequence, and one candidate-only real execution after all five
commands pass. It publishes record 110 with complete authority, raw-tree, report,
candidate-plan, manifest, storage, membership, and source evidence. Review 109 contains the
complete task; no out-of-band instruction is authority.

No plan migration, sample acquisition, amendment-ledger creation, Gate 2, normalization,
catalog work, Nautilus work, Harmonic Trader work, or other-ticket work is authorized. A
nonzero focused-command exit stops immediately before all later commands and the real
candidate process. Gate 1 remains `IN_PROGRESS`; next ticket remains `NONE`.

## Review-110 focused execution outcome - rejected

Review 111 accepts Hermes's exact two-path integration and strict stop after focused
command 1 failed 2 of 189 cases. Commands 2 through 5 and the real candidate process were
correctly not run. Both remaining identity differences are the local prospective-holdout
`record_path`: independently created test roots contain `/clean/` versus `/resumed/`.

Sr Dev - Claude Build using Claude Opus 5 is authorized only to add `record_path` to the
execution-plane identity drop-key set. All semantic holdout boundary times, identifiers,
lineage, replay state, and complete identity tests remain unchanged. Only the production
module may change; the test path, CLI, 17 fixtures, holdout implementation, manifest,
taker-flow, locked plan, and ledger behavior are frozen.

Claude performs no tests, network/data run, migration, integration, repository-record
edit, Git, acquisition, catalog work, Nautilus work, Harmonic Trader work, or publication
and stops for reviewer inspection with the exact source hash. Hermes and real candidate
execution remain unauthorized. Gate 1 remains `IN_PROGRESS`; next ticket remains `NONE`.

## Claude review-111 source outcome - accepted for integration

Review 112 accepts the exact one-path source correction after static review. Only the
local prospective-holdout `record_path` is excluded from semantic identity; every boundary
time, identifier, lineage digest, replay rule, state, and outcome-blind assertion remains
included. The test path, CLI, and 17 fixtures remain unchanged.

Jr Dev - Hermes is authorized only for review 112's exact one-path integration, strict
stop-on-first-failure focused sequence, and one candidate-only real execution after all five
commands pass. It publishes record 113 with complete authority, raw-tree, report,
candidate-plan, manifest, storage, membership, and source evidence. Review 112 contains the
complete task; no out-of-band instruction is authority.

No plan migration, sample acquisition, amendment-ledger creation, Gate 2, normalization,
catalog work, Nautilus work, Harmonic Trader work, or other-ticket work is authorized. A
nonzero focused-command exit stops immediately before all later commands and the real
candidate process. Gate 1 remains `IN_PROGRESS`; next ticket remains `NONE`.

## Review-113 candidate timeout outcome

Review 114 accepts the exact production integration and the strict passing sequence of 189
CEX-002 tests, 11 atomic-download tests, Ruff, repository control, and committed-diff
whitespace inspection. No implementation correction or focused-command rerun is
authorized. The candidate execution itself is rejected as terminal evidence because
record 113 omitted its required before snapshot and process status, and incorrectly claimed
no mutation even though the resumable listing checkpoint and cache advanced.

Jr Dev - Hermes is authorized only for review 114's one measured 50-minute resume slice
against the preserved store. It captures the complete before snapshot, invokes the exact
candidate command once under the specified timeout, captures status immediately, repeats
the complete snapshot on every exit path, and publishes record 115. A status 124 records
progress and stops; it does not authorize another invocation. Review 114 is the complete
task and no out-of-band instruction is authority.

No source/test edit, focused test rerun, store reconstruction, cache reset, plan migration,
sample acquisition, amendment-ledger creation, Gate 2, normalization, catalog work,
Nautilus work, Harmonic Trader work, or other-ticket work is authorized. Gate 1 remains
`IN_PROGRESS`; next ticket remains `NONE`.

## Review-115 measured resume outcome

Review 116 accepts the status-124 execution evidence and the proved authority/raw/report
invariants. Hermes advanced the checkpoint by 561 entries and captured the complete
before/after state. Its unauthorized rerun of the already accepted 189-test suite is a
governance violation and is not new acceptance evidence, but it does not invalidate the
separately measured candidate execution.

Further serial resume slices are rejected. The current path creates a fresh HTTP client per
page, rewrites the complete 25 MB checkpoint per new page, and traverses thousands of
family/symbol/page requests serially. ADR-0018 preserves the complete data contract while
requiring reusable bounded transport resources, bounded deterministic listing concurrency,
amortized crash-recoverable checkpoint publication, and efficient known-cache bootstrap.

Sr Dev - Claude Build using Claude Opus 5 is authorized only for review 116's five-path
source/test correction. Claude performs no tests, network/data run, candidate execution,
integration, records, ADR, Git, catalog work, Nautilus work, or Harmonic Trader work and
stops for source inspection with exact changed-path hashes and the unique CEX test-function
count. Hermes and further real execution remain unauthorized. Gate 1 remains
`IN_PROGRESS`; next ticket remains `NONE`.

## Claude review-116 listing source outcome - rejected

Review 117 accepts the bounded transport/concurrency and amortized crash-recovery direction
but rejects the five-path drop before integration. A fresh store raises `KeyError` on the
new bootstrap field; at least seven accumulated tests are incompatible with the new
durability/transport contracts; pooled-client first construction, checkpoint counters, and
retry evidence are not fully deterministic under concurrency; and a failed checkpoint
write clears pending state before publication succeeds. Cleanup can also skip checkpoint
flush when client close raises, and library callers became concurrent by default.

ADR-0018 now clarifies that serial-versus-bounded proof compares semantic identity,
canonical request-to-content mappings, and incident order after normalizing only real
retrieval timestamps. Sr Dev - Claude Build using Claude Opus 5 is authorized only for
review 117's surgical correction in the same five paths. Claude runs no commands or data,
touches no records or Git, and stops for source review with exact hashes and both unique
test-function counts.

Hermes, integration, tests, and real execution remain unauthorized. No data-scope change,
cache reset, plan migration, sample acquisition, Gate 2, normalization, catalog work,
Nautilus work, Harmonic Trader work, or other-ticket work is authorized. Gate 1 remains
`IN_PROGRESS`; next ticket remains `NONE`.

## Claude review-117 listing correction outcome - main module accepted, residue rejected

Review 118 accepts and freezes the main qualification module at SHA-256
`b6077bf833ae59b2414b441564764179fc0dcff0db6cec3457139a5a26df53e8`.
The cold path, stale accumulated tests, pooled first-use race, checkpoint counters,
failed-flush state, retry ordering implementation, and serial library default are closed.

Integration remains unauthorized because the serial-versus-bounded test reads checkpoint
files its memory indexes never create; combined cleanup failures do not preserve the
declared primary error; a failed client close increments the successful-close counter; and
the retry-order test sorts hand-built rows without executing inverted concurrent retries.

Sr Dev - Claude Build using Claude Opus 5 is authorized only for review 118's four-path
CLI/shared-transport/test correction. The main qualification module and 17 fixtures are
frozen. Claude runs no commands or data, touches no records or Git, and stops for source
review with exact hashes and both unique test-function counts.

Hermes, integration, tests, and real execution remain unauthorized. No data-scope change,
cache reset, plan migration, sample acquisition, Gate 2, normalization, catalog work,
Nautilus work, Harmonic Trader work, or other-ticket work is authorized. Gate 1 remains
`IN_PROGRESS`; next ticket remains `NONE`.

## Claude review-118 residual outcome - implementation accepted, CEX tests rejected

Review 119 accepts and freezes the main qualification module, CLI, shared pooled transport,
and atomic-download tests. Cleanup now preserves body-error precedence and first-cleanup
failure precedence, failed client close is not counted as success, and the checkpoint
mapping proof uses real checkpoint-enabled indexes.

Only the CEX test source remains rejected. One accumulated test still expects cleanup to
replace an active qualification failure, contrary to the corrected CLI. The concurrent
retry test raises raw `httpx.ConnectError`, which is intentionally outside the retryable
`DownloadError` contract, so it produces no incident journal.

Sr Dev - Claude Build using Claude Opus 5 is authorized only for review 119's one-path,
two-test correction. Every production/CLI/atomic path and all fixtures are frozen. Claude
runs no commands or data, touches no records or Git, and stops for source review with the
exact test hash, frozen hashes, and unique test-function count.

Hermes, integration, tests, and real execution remain unauthorized. No data-scope change,
cache reset, plan migration, sample acquisition, Gate 2, normalization, catalog work,
Nautilus work, Harmonic Trader work, or other-ticket work is authorized. Gate 1 remains
`IN_PROGRESS`; next ticket remains `NONE`.

## Claude review-119 test-only outcome - accepted for Hermes integration

Review 120 accepts the complete five-path ADR-0018 source/test drop. Both review-119 test
defects are closed: cleanup-body precedence is asserted against the corrected CLI, and the
concurrent retry proof now uses retryable `DownloadError` failures with canonical redacted
report and durable-journal evidence. All four previously frozen hashes still match; the
CEX and atomic files contain 186 and 18 unique tests, respectively; all 17 CEX fixtures
remain unchanged.

Jr Dev - Hermes is authorized only for review 120's exact five-path integration,
stop-on-first-failure five-command sequence, complete before/after measurements, and one
50-minute candidate-only continuation against the existing checkpoint and caches after all
commands pass. It publishes record 121 and stops for review on every candidate status.
Review 120 is the complete task; no out-of-band instruction is authority.

No source/test/fixture edit, reset, cleanup, cache reconstruction, reduced data scope, plan
migration, sample acquisition, Gate 2, normalization, catalog publication, Nautilus work,
Harmonic Trader work, payoff analysis, PAPER, LIVE, or other-ticket work is authorized.
Gate 1 remains `IN_PROGRESS`; next ticket remains `NONE`.

## Review-121 terminal candidate outcome - execution accepted, report architecture rejected

Review 122 accepts the exact five-path integration and the terminal status-2 candidate
execution. ADR-0018 reduced the complete remaining listing run to 1,963 seconds: 30,172
requests reused, 9,640 fetched, one pooled client opened/closed, and only 39 checkpoint
serializations. The lock, ledger, retained raw tree, and amendment-ledger absence remained
exact. The candidate remains honestly blocked and performed no migration or sample
download.

The 1,059,297,547-byte report is not publishable. It serializes 733,203 detailed manifest
rows twice, once at top level and once under storage. ADR-0019 requires a compact tracked
receipt cryptographically bound to one complete, deterministic, content-addressed,
stream-verifiable detail artifact under the ignored data root. No universe, field, row,
lineage, or evidence is dropped; Git LFS and external storage are rejected.

Sr Dev - Claude Build using Claude Opus 5 is authorized only for review 122's exact
three-path ADR-0019 source/test implementation. The current oversized report and all data
are frozen. Claude runs no commands, touches no records or Git, and stops for source review
with exact hashes and the unique test-function count. Hermes and any report/candidate rerun
remain unauthorized.

No reduced scope, report truncation, plan migration, sample acquisition, Gate 2,
normalization, catalog publication, Nautilus work, Harmonic Trader work, payoff analysis,
PAPER, LIVE, or other-ticket work is authorized. Gate 1 remains `IN_PROGRESS`; next ticket
remains `NONE`.

## Claude ADR-0019 source outcome - rejected before integration

Review 123 accepts the split-writer direction but rejects the three-path drop. The public
iterator yields detail rows before its final digest/count checks, so a consumer may use
unvalidated evidence or stop before validation. The reader does not compare compressed
hash/size, schema/format identity, or recompute row totals/family/pending authority. It
also accepts noncanonical JSON and some non-relative paths. Publication failure proofs do
not reach partial-write/replace boundaries, the writer sorts the full 733,203-row
collection despite its bounded-memory claim, and one no-duplication assertion is vacuous.

Sr Dev - Claude Build using Claude Opus 5 is authorized only for review 123's same
three-path correction. It preserves the split architecture and all accepted source/data
semantics, runs no commands, touches no data/records/Git, and stops for source review with
exact hashes and the unique test-function count. The preserved 1.06 GB report remains
frozen. Hermes and report rerun remain unauthorized.

No reduced scope, report truncation, plan migration, sample acquisition, Gate 2,
normalization, catalog publication, Nautilus work, Harmonic Trader work, payoff analysis,
PAPER, LIVE, or other-ticket work is authorized. Gate 1 remains `IN_PROGRESS`; next ticket
remains `NONE`.

## Claude correction interrupted - Grok continuation authorized

Claude exhausted its four-hour usage window before completing review 123. Review 124
records exact hashes for the preserved partial production/test correction and transfers
the same bounded three-path task to Sr Dev - Grok Build using Grok 4.6 High. The partial
drop is an unfinished continuation base, not an accepted result.

Grok must continue the current diff in place and close every review-123 validation,
bounded-streaming, atomic-publication, and test-proof finding. It runs no commands, touches
no data/records/Git, and stops for reviewer source inspection with exact hashes and the
unique test-function count. The 1.06 GB report remains frozen; Hermes and report rerun
remain unauthorized. Review 124 is the complete transfer authority and no out-of-band
prompt is authority.

No reduced scope, report truncation, plan migration, sample acquisition, Gate 2,
normalization, catalog publication, Nautilus work, Harmonic Trader work, payoff analysis,
PAPER, LIVE, or other-ticket work is authorized. Gate 1 remains `IN_PROGRESS`; next ticket
remains `NONE`.

## Grok report-split continuation outcome - one bounded-memory defect remains

Review 125 accepts Grok's prevalidation, identity, aggregate, canonical encoding/path,
atomic-publication, bounded-writer, and test-proof corrections, but rejects the drop before
Hermes integration. The validator's claimed bounded pass retains every selected row key in
`row_keys`; with 733,203 rows this is O(n) auxiliary memory and leaves review 123's explicit
bounded duplicate-check requirement open. The boundedness test covers only the writer.

Sr Dev - Grok Build using Grok 4.6 High is authorized only for review 125's surgical
production/test correction. It must establish a canonical key-primary row order once at
manifest construction, detect duplicate keys and order failures with constant retained
state, remove the whole-key set, and add a direct validator-boundedness proof while
preserving every accepted behavior. The unchanged CLI hash is frozen. Grok runs no
commands or data, touches no records or Git, and stops for source review with exact hashes
and the unique test-function count. Hermes remains unauthorized.

The oversized report remains frozen. No reduced scope, report truncation, plan migration,
sample acquisition, Gate 2, normalization, catalog publication, Nautilus work, Harmonic
Trader work, payoff analysis, PAPER, LIVE, or other-ticket work is authorized. Gate 1
remains `IN_PROGRESS`; next ticket remains `NONE`.

## Grok residual correction outcome - accepted for Hermes integration

Review 126 accepts the complete ADR-0019 three-path source/test drop. Manifest rows are
canonicalized by physical-object key at construction, the validator now retains only the
prior key while proving order and duplicate rejection, and the validator itself has
focused bounded-state proof. The complete drop contains 209 unique CEX test functions;
the CLI and the previously accepted atomic-download dependency remain exact.

Jr Dev - Hermes is authorized only for review 126's exact integration, stop-on-first-
failure five-command sequence, atomic content-addressed preservation of the current
1,059,297,547-byte report, before/after measurements, and one 50-minute candidate-only
execution against the completed checkpoint and caches. It publishes record 127 and the
resulting compact report when valid, commits and pushes only the enumerated paths, and
stops for reviewer inspection on every candidate status. No reset, restore, stash, clean,
or automatic second candidate invocation is authorized.

No reduced scope, report truncation, plan migration, sample acquisition, Gate 2,
normalization, catalog publication, Nautilus work, Harmonic Trader work, payoff analysis,
PAPER, LIVE, or other-ticket work is authorized. Gate 1 remains `IN_PROGRESS`; next ticket
remains `NONE`.

## Review-127 focused-command outcome - two stale tests rejected

Review 128 accepts Hermes's exact three-path integration and stop-on-first-failure
discipline. Command 1 collected 256 items and stopped at 2 failed / 254 passed; commands
2-5, monolith preservation, and the candidate correctly did not run. The 1.06 GB report
and all data remain unchanged.

Both failures are reviewer-accepted test defects. ADR-0019 intentionally makes
`storage.acquisition_manifest` a summary rather than a second detailed owner, so expecting
`storage.acquisition_manifest.rows` is stale. The three selected keys found elsewhere in
the receipt are legitimate bounded `sample_plan` entries; global key presence does not
prove duplication of a complete manifest-row object.

Implementation Dev - Codex Spark using GPT-5.3-Codex-Spark High is authorized only for
review 128's exact two-assertion correction in the single CEX test path. Production, CLI,
atomic dependency, fixtures, report, and data are frozen. Spark runs no commands, edits no
records, and performs no Git operation. It stops for reviewer source inspection with the
test hash and 209 unique test-function count. Hermes and candidate execution remain
unauthorized.

No reduced scope, report truncation, plan migration, sample acquisition, Gate 2,
normalization, catalog publication, Nautilus work, Harmonic Trader work, payoff analysis,
PAPER, LIVE, or other-ticket work is authorized. Gate 1 remains `IN_PROGRESS`; next ticket
remains `NONE`.

## Spark review-128 test outcome - one residual assertion rejected

Review 129 accepts and freezes Spark's storage-summary correction. The compact-receipt
test now rejects any 13-field mapping, but its claimed legitimate-overlap proof merely
shows that some sample-plan key appears in a receipt that necessarily contains the sample
plan. It never proves that a selected manifest key is the legitimate plan reference, and
it does not implement review 128's exact full-row serialization comparison.

Implementation Dev - Codex Spark using GPT-5.3-Codex-Spark High is authorized only for
review 129's residual local assertion-block rewrite in the same CEX test path. It compares
each complete selected row's compact canonical JSON with the compact parsed receipt, and
proves a nonempty intersection between selected keys and serialized sample-plan keys.
Spark runs no commands, touches no other block or path, and performs no Git operation. It
stops with the test hash and unchanged 209-function count. Hermes remains unauthorized.

No reduced scope, report truncation, plan migration, sample acquisition, Gate 2,
normalization, catalog publication, Nautilus work, Harmonic Trader work, payoff analysis,
PAPER, LIVE, or other-ticket work is authorized. Gate 1 remains `IN_PROGRESS`; next ticket
remains `NONE`.

## Spark residual test outcome - accepted for Hermes integration

Review 130 accepts Spark's single CEX test path at its exact hash and 209 unique test
functions. The storage block is proved summary-only, complete manifest-row objects are
absent from the compact receipt, and legitimate selected-key/sample-plan overlap is
proved without confusing key references with row duplication. Production and CLI remain
frozen at their integrated review-126 hashes.

Jr Dev - Hermes is authorized only for review 130's exact test integration and the complete
review-126 operational sequence: all five commands restart at command 1; only if all pass
does Hermes atomically preserve the monolith, capture snapshots, and run the candidate once
under the same 50-minute bound. It publishes record 131 and the valid compact report when
produced, uses only enumerated commits, pushes, and stops for reviewer inspection. No
reset, restore, stash, clean, or automatic second candidate invocation is authorized.

No reduced scope, report truncation, plan migration, sample acquisition, Gate 2,
normalization, catalog publication, Nautilus work, Harmonic Trader work, payoff analysis,
PAPER, LIVE, or other-ticket work is authorized. Gate 1 remains `IN_PROGRESS`; next ticket
remains `NONE`.

## Record-131 focused-command outcome - two mechanical Ruff findings

Review 132 accepts Hermes's test-only integration and command discipline. C1 passed all
256 CEX items, C2 passed all 18 atomic items, and C3 stopped on F402 in the frozen
production module plus F841 in the accepted CEX test. C4/C5, preservation, and the
candidate correctly did not run. The report and data remain unchanged.

The record-131 publication left this file's next actor stale while updating the ticket;
review 132 repairs that control mismatch directly. Implementation Dev - Codex Spark using
GPT-5.3-Codex-Spark High is authorized only to rename the local Coinalyze loop variable
`fields` to `point_fields` and its one use, and delete the unused test assignment
`rendered = receipt_path.read_bytes()`. Spark runs no commands, touches no other line or
path, and performs no Git operation. It stops with both hashes and the unchanged 209-test
function count. Hermes remains unauthorized.

No reduced scope, report truncation, plan migration, sample acquisition, Gate 2,
normalization, catalog publication, Nautilus work, Harmonic Trader work, payoff analysis,
PAPER, LIVE, or other-ticket work is authorized. Gate 1 remains `IN_PROGRESS`; next ticket
remains `NONE`.

## Spark Ruff correction outcome - accepted for Hermes integration

Review 133 accepts Spark's exact two-path mechanical correction. The Coinalyze loop local
no longer shadows `dataclasses.fields`, the obsolete receipt bytes assignment is removed,
and the 209-test-function contract is unchanged. No behavior, assertion, or authority
changed.

Jr Dev - Hermes is authorized only to integrate the two accepted hashes, restart all five
focused commands at command 1, and proceed after all pass with review 126's exact atomic
monolith preservation, snapshots, one 50-minute candidate, validation, and publication
contract. It writes record 134, commits and pushes only enumerated paths, and stops for
reviewer inspection. No reset, restore, stash, clean, migration, sample acquisition,
Gate 2, or automatic second candidate invocation is authorized.

No reduced scope, report truncation, normalization, catalog publication, Nautilus work,
Harmonic Trader work, payoff analysis, PAPER, LIVE, or other-ticket work is authorized.
Gate 1 remains `IN_PROGRESS`; next ticket remains `NONE`.

## Record-136 forward correction published

Hermes published `research/sprint_004/136_CEX002_RECORD_134_CORRECTION.md` as the forward
correction required by review 135. Record 134 remains preserved. The correction records
the exact integration identities, the correct review-133 integration commit `dba025c`, the
unavailable original C5 transcript, the corrected FAPI cache counts and byte totals, the
correct manifest phase order, and the correct iterator/header arithmetic.

Every other accepted record-134 candidate, artifact, invariant, mutation, and stop claim
remains unchanged. CEX-002 remains `IN_PROGRESS`; Gate 1 has not passed; next ticket
remains `NONE`.

## Review-137 architecture and Claude source authorization

Review 137 accepts record 136 and ADR-0020 resolves the historical-name authority and
qualification-budget architecture. The review itself freezes the exact 46 delivery
identities, all 17 alias-to-base mappings, their authority classes, the qualification
strata formula, and candidate-version lineage.

Sr Dev - Claude Build using Claude Opus 5 is authorized only for the three Python paths
and optional existing fixture directory enumerated in review 137. Claude implements all
ten numbered requirements and focused test-source coverage there, without executing tests,
Ruff, network/data work, the candidate, Git, migration, acquisition, or any repository
record. It stops for reviewer source inspection with exact SHA-256 values for every edited
path and the unique CEX test-function count. Hermes remains unauthorized.

No Gate-1 candidate execution, sample acquisition, plan migration, Gate 2, reduced scope,
Nautilus, Harmonic Trader, payoff, PAPER, LIVE, or next-ticket work is authorized. CEX-002
remains `IN_PROGRESS`; next ticket remains `NONE`.

## Claude ADR-0020 source outcome - correction required

Review 138 accepts and freezes the CLI wiring but rejects the production and test source.
The authority-table digests are recomputed from mutable tables rather than checked against
independent review constants; cost samples receive only first-line schema inference instead
of full parse/time/economic validation, including on retained reuse; the complete Gate-2
cost manifest publishes no digest; delivery-price finite/provenance checks are incomplete;
and the test import list contains duplicate names.

Sr Dev - Claude Build using Claude Opus 5 is authorized only for review 138's bounded
production/test correction. The CLI and all other paths are frozen. Claude runs no command
or network/data work, performs no Git or repository-record operation, and stops with the
two exact hashes and unique CEX test-function count. Hermes remains unauthorized.

No candidate integration/execution, migration, acquisition, Gate 2, reduced scope,
Nautilus, Harmonic Trader, payoff, PAPER, LIVE, or next-ticket work is authorized. CEX-002
remains `IN_PROGRESS`; next ticket remains `NONE`.

## Claude review-138 correction outcome - four residuals remain

Review 139 accepts and freezes the independent authority-table boundary, delivery-price
correction, cost economic rules and three acquisition-path wiring, complete-manifest digest
domain/report binding, selection, and candidate lineage. It rejects four narrow residuals:
cost ZIP validation still ignores every member after the first and does not use structured
CSV parsing; the version-4 builder permits an empty complete-manifest digest; one retained-
content test now reaches the preceding filename check; and the test file has a blank EOF.

Sr Dev - Claude Build using Claude Opus 5 is authorized only for review 139's four exact
production/test corrections. Every accepted region, the CLI, fixtures, and all other paths
are frozen. Claude runs no command or network/data work, performs no Git or repository-
record operation, and stops with the two exact hashes and unique CEX test-function count.
Hermes remains unauthorized.

No candidate integration/execution, migration, acquisition, Gate 2, reduced scope,
Nautilus, Harmonic Trader, payoff, PAPER, LIVE, or next-ticket work is authorized. CEX-002
remains `IN_PROGRESS`; next ticket remains `NONE`.

## ADR-0020 source accepted - Hermes integration and one candidate

Review 140 accepts the exact production, CLI, and 261-test source identities. Review 139's
single-member strict CSV proof, mandatory complete-cost identity, retained-content test,
and clean-diff residuals are closed. The complete ADR-0020 authority, cost validation,
manifest identity, qualification priority, and version-4 lineage source is accepted for
runtime proof; no runtime result is inferred from source inspection.

Jr Dev - Hermes is authorized only for review 140's exact three-path integration, five
stop-on-first-failure focused commands, content-address preservation of the accepted compact
report, one bounded candidate-only execution, complete post-proof, record 141, enumerated
publication, commit, and push. It edits no source/test after integration and touches no
unrelated dirty path.

No plan migration, sample acquisition, Gate 2, reduced scope, Nautilus, Harmonic Trader,
payoff, PAPER, LIVE, or next-ticket work is authorized. CEX-002 remains `IN_PROGRESS`;
next ticket remains `NONE`.

## Record-141 integration stop published

Hermes integrated review 140's exact three accepted paths in commit `68d437c` and pushed
it. The required focused sequence stopped at command 1:
`.venv/bin/python -m pytest tests/acquisition/test_binance_usdm_harmonic_qualification.py -q --tb=short`
returned exit 1 on
`test_frozen_delivery_identity_resolves_only_while_its_evidence_reproves`, where the
expected archive family count was 2 and the observed value was 3.

Commands 2-5, compact-report preservation, candidate execution, post-proof, report
publication, migration, sample acquisition, Gate 2, and later work were not run. CEX-002
remains `IN_PROGRESS`; Gate 1 has not passed; next ticket remains `NONE`.

## Record-141 stop accepted - one stale test assertion

Review 142 accepts the exact review-140 integration, record 141, unchanged compact report,
and stop-on-first-failure behavior. Production correctly reports all three archive families
created by the test fixture; the test incorrectly compares that observed count with the
two-family minimum threshold.

Implementation Dev - Codex Spark changes only the one assertion in
`test_frozen_delivery_identity_resolves_only_while_its_evidence_reproves` from
`family_count == 2` to `family_count == 3`. Spark changes nothing else, runs no command,
uses no Git, and returns the test hash plus the unchanged 261-test count. Hermes remains
unauthorized.

No candidate, migration, acquisition, Gate 2, reduced scope, Nautilus, Harmonic Trader,
payoff, PAPER, LIVE, or next-ticket work is authorized. CEX-002 remains `IN_PROGRESS`;
next ticket remains `NONE`.

## Spark focused test correction accepted - Hermes restart authorized

Review 143 accepts Spark's exact one-assertion correction at test SHA-256
`186eccc22df2eb8f49f8f004141b6be7efdae15080afefa0675cfbd26e7a3fdd`. The test now
expects the three official archive families supplied by its fixture, while production's
two-family minimum remains unchanged. The file retains exactly 261 unique tests; every
frozen production, CLI, dependency, fixture, and compact-report identity still matches.

Jr Dev - Hermes is authorized only for review 143's exact test integration, full five-
command restart, and, after all five pass, the accepted compact-report preservation,
single 50-minute candidate-only invocation, complete post-proof, record 144, enumerated
publication, commits, and pushes. Hermes stops at the first command failure and makes no
automatic second candidate invocation.

No source/test edit after integration, unrelated dirty-path mutation, plan migration,
sample acquisition, Gate 2, reduced scope, Nautilus, Harmonic Trader, payoff, PAPER, LIVE,
or next-ticket work is authorized. CEX-002 remains `IN_PROGRESS`; Gate 1 has not passed;
next ticket remains `NONE`.

## Record-144 version-4 candidate published

Hermes integrated review 143's exact one-assertion test correction in commit `56dc471` and
ran all five focused commands successfully. Hermes then preserved the accepted compact
report, ran exactly one candidate-only invocation, and published record 144 plus the
replacement compact report.

The candidate returned terminal status 2 with `gate_status=BLOCKED` and `accepted=false`.
The version-4 candidate resolves the 46 reviewed delivery identities and 17 settlement
aliases, leaving zero unresolved archive names, but the product matrix remains incomplete
with seven blocked products. Candidate migration and download remain false, samples remain
empty, and Gate 1 has not passed.

No plan migration, sample acquisition, Gate 2, reduced scope, Nautilus, Harmonic Trader,
payoff, PAPER, LIVE, or next-ticket work is authorized. CEX-002 remains `IN_PROGRESS`;
next ticket remains `NONE`.

## Version-4 candidate accepted - migration source required

Review 145 accepts Hermes's exact test integration, all five exit-0 focused commands,
terminal status-2 candidate, compact report, preserved reports, and ADR-0020 authority and
cost proofs. All 46 reviewed deliveries and 17 settlement aliases resolve; zero archive
names remain unresolved. Samples are still empty, seven source products remain blocked,
and Gate 1 has not passed.

The current source has no valid 2-to-4 migration or independent-amendment-ledger execution
path, so Hermes is not authorized to mutate the live plan. ADR-0020 now fixes a one-shot,
ledger-first/lock-last transaction that preserves versions 0-2, keeps the version-3
candidate as unmigrated lineage, binds the exact reviewed version-4 plan and source
identity, and stops before sample acquisition.

Sr Dev - Claude Build using Claude Opus 5 is authorized only for review 145's exact three-
path migration production/CLI/test-source implementation. Claude runs no command, network
or data operation, migration, repository-record edit, or Git operation and stops for
reviewer source inspection with three hashes and the unique test-function count.

No live migration, sample acquisition, Gate 2, reduced scope, Nautilus, Harmonic Trader,
payoff, PAPER, LIVE, or next-ticket work is authorized. CEX-002 remains `IN_PROGRESS`;
Gate 1 has not passed; next ticket remains `NONE`.

## Claude migration source rejected - bounded correction required

Review 146 rejects Claude's first migration source drop. In the prepared-ledger/version-2
interruption state, an ordinary invocation can still enter legacy execution, contrary to
the migration-only recovery contract. The real CLI also overwrites the exact accepted
candidate report after committing the lock, so its next preflight cannot re-prove the
authority it just destroyed. Completed-state lock/ledger binding, prior-lock evidence,
history/inputs, and amendment accounting are not yet proved completely.

Sr Dev - Claude Build using Claude Opus 5 is authorized only for review 146's correction
in the same three Python paths. Claude implements the explicit ordinary state matrix,
read-only migration report handling, complete shared migrated-state validation, strict
reviewed-plan allowance accounting, and focused real-CLI/interruption/tamper test source.
Claude runs no command, test, Ruff, network/data work, migration, integration, record edit,
or Git operation and stops with the three exact hashes and unique test-function count.
Hermes remains unauthorized.

No live migration, sample acquisition, Gate 2, reduced scope, Nautilus, Harmonic Trader,
payoff, PAPER, LIVE, or next-ticket work is authorized. CEX-002 remains `IN_PROGRESS`;
Gate 1 has not passed; next ticket remains `NONE`.

## Claude correction interrupted - Grok continuation authorized

Claude Opus 5 exhausted its available context after partially editing only the production
path. Review 147 records the exact three continuation hashes and reassigns the complete
review-146 correction to Sr Dev - Grok Build using Grok 4.6 High. Claude is no longer the
authorized senior actor for this drop.

Grok continues in the same three paths without reset, restore, wholesale replacement,
command execution, Git, or repository-record edits. The unchanged rejected CLI and tests,
ordinary-input validation ordering, and exact migrated-history proof remain unfinished;
every review-146 requirement remains binding. Grok stops with all three exact hashes and
the unique test-function count. Hermes remains unauthorized.

No live migration, sample acquisition, Gate 2, reduced scope, Nautilus, Harmonic Trader,
payoff, PAPER, LIVE, or next-ticket work is authorized. CEX-002 remains `IN_PROGRESS`;
Gate 1 has not passed; next ticket remains `NONE`.

## Grok migration continuation rejected - two residuals

Review 148 accepts the mixed-state refusal, CLI report preservation, current-input
ordering, exact prior-history evidence, full lock/ledger comparison, and reviewed-plan
accounting directions, but rejects the drop before Hermes integration. Migration-only
still records or unconditionally flushes the sample checkpoint, and a self-consistent
lock-plus-ledger edit can substitute the executing source receipt because only its shape
is checked. The ledger loader also coerces a non-object JSON binding through `dict()`.

Sr Dev - Grok Build using Grok 4.6 High is authorized only for review 148's residual
production/test correction in the same three paths. Grok makes migration checkpoint use
strictly read-only, binds the installed final source receipt to the exact executing source
and lock input, rejects non-object/malformed binding and receipt structures, and adds the
direct sentinel and two-file substitution proofs. It runs no command or Git operation and
stops with all three hashes and the unique test-function count. Hermes remains
unauthorized.

No live migration, sample acquisition, Gate 2, reduced scope, Nautilus, Harmonic Trader,
payoff, PAPER, LIVE, or next-ticket work is authorized. CEX-002 remains `IN_PROGRESS`;
Gate 1 has not passed; next ticket remains `NONE`.

## Grok residual production accepted - one Spark test correction

Review 149 accepts and freezes the corrected production and unchanged CLI hashes. Migration
retained recovery and terminal reporting no longer mutate the sample checkpoint, and the
installed amendment binding now rejects malformed types and binds its final receipt to the
exact live source plus lock code/config input.

The test source is rejected on one local harness error. The prepared-interruption test
calls `monkeypatch.undo()`, which removes the fixture's reviewed identity constants before
the second migration and makes valid recovery fail preflight. Implementation Dev - Codex
Spark using GPT-5.3-Codex-Spark High is authorized only to scope restoration to
`install_migrated_lock` inside that test and retain the checkpoint-sentinel/byte proofs
through recovery. Spark changes no other byte, runs no command or Git operation, and
returns the test hash with the unchanged 285-test count. Hermes remains unauthorized.

No live migration, sample acquisition, Gate 2, reduced scope, Nautilus, Harmonic Trader,
payoff, PAPER, LIVE, or next-ticket work is authorized. CEX-002 remains `IN_PROGRESS`;
Gate 1 has not passed; next ticket remains `NONE`.

## Spark restoration repair accepted - final recovery assertions missing

Review 150 accepts Spark's local restoration of only `install_migrated_lock`; the
fixture-specific reviewed constants and checkpoint watcher now remain active through the
recovery migration. The test path is still rejected because Spark omitted review 149's
required post-recovery assertions for no checkpoint `record()`, no checkpoint `flush()`,
and byte-identical checkpoint state.

Implementation Dev - Codex Spark using GPT-5.3-Codex-Spark High is authorized only to add
those three assertions after the successful recovery in the same test function. Every
other byte remains frozen. Spark runs no command or Git operation and returns the exact
test hash with the unchanged 285-test count. Hermes remains unauthorized.

No live migration, sample acquisition, Gate 2, reduced scope, Nautilus, Harmonic Trader,
payoff, PAPER, LIVE, or next-ticket work is authorized. CEX-002 remains `IN_PROGRESS`;
Gate 1 has not passed; next ticket remains `NONE`.

## Migration source accepted - Hermes integration and migration-only execution

Review 151 accepts and freezes the exact production, CLI, and 285-test source identities.
The reviewed migration is fail-closed, ledger-first/lock-last, keeps the accepted report
read-only, binds the installed authority to the exact executing source/config, and does
not enter sample acquisition or mutate the sample checkpoint.

Jr Dev - Hermes is authorized for review 151's exact-hash three-path integration,
stop-on-first-failure focused commands, one preconditioned
`--apply-reviewed-v4-migration-only` invocation, complete before/after proof, and record
152 publication. Status 2 is the expected terminal qualification status after a successful
migration because Gate 1 remains blocked. Hermes performs no ordinary resume or second
migration invocation and downloads no sample.

No sample acquisition, Gate 2, reduced scope, Nautilus, Harmonic Trader, payoff, PAPER,
LIVE, or next-ticket work is authorized. CEX-002 remains `IN_PROGRESS`; Gate 1 has not
passed; next ticket remains `NONE`.

## Record-152 migration integration stop published

Hermes integrated review 151's exact three accepted paths in commit `bce618f` and pushed
it. The required focused sequence stopped at command 1:
`.venv/bin/python -m pytest tests/acquisition/test_binance_usdm_harmonic_qualification.py -q --tb=short`
returned exit 1 with 15 migration-test failures. The repeated central mismatch was an
installed/migration plan digest of `d3fe13d9...` where tests expected the accepted
version-4 digest `2fb0e47a...`.

Commands 2-5, migration preconditions, the migration-only invocation, ordinary resume,
sample acquisition, Gate 2, and later work were not run. CEX-002 remains `IN_PROGRESS`;
Gate 1 has not passed; next ticket remains `NONE`.

## Focused migration tests rejected - Grok fixture correction

Review 153 accepts Hermes's exact integration and required stop, and keeps the integrated
production and CLI source frozen. The 15 failures reduce to three test-only defects: the
fixture patches production-module migration identities but its assertions read stale
imported literals; seeding and candidacy use the same fully acquired inventory so the
candidate has no download entries; and one fail-closed assertion expects a different
message than the exact binding validator emits.

Sr Dev - Grok Build using Grok 4.6 High is authorized only for review 153's correction in
`tests/acquisition/test_binance_usdm_harmonic_qualification.py`. Grok aligns fixture-scoped
test identities without weakening the production-literal test, makes the real planner
produce at least two candidate downloads while retaining at least one object, and corrects
the wrong-authority ledger proof/message. It changes no production/CLI byte, runs no
command or Git operation, and returns the test hash plus unchanged 285-test count. Hermes
remains unauthorized pending source acceptance.

No migration invocation, sample acquisition, Gate 2, reduced scope, Nautilus, Harmonic
Trader, payoff, PAPER, LIVE, or next-ticket work is authorized. CEX-002 remains
`IN_PROGRESS`; Gate 1 has not passed; next ticket remains `NONE`.

## Migration test correction accepted - Hermes restart authorized

Review 154 accepts and freezes Grok's exact test correction at
`a753afc0290708c630198714d574f1ddb65fa43e97b516a100ba32f0a915fd1e`. The fixture now
aligns generated identities in both namespaces, derives retained and download entries
through the real planner, and isolates the wrong-binding error with a valid source receipt.
The integrated production and CLI hashes remain frozen.

Jr Dev - Hermes is authorized for review 154's exact test-only integration and a complete
restart of review 151's C1-C5 stop-on-first-failure sequence. Only if all five commands
pass may Hermes perform review 151's exact migration preconditions, single migration-only
invocation, after-proof, and record 155 publication. No retry, ordinary resume, second
migration, or sample acquisition is authorized.

No migration before all focused commands pass, sample acquisition, Gate 2, reduced scope,
Nautilus, Harmonic Trader, payoff, PAPER, LIVE, or next-ticket work is authorized. CEX-002
remains `IN_PROGRESS`; Gate 1 has not passed; next ticket remains `NONE`.

## Record-155 migration test integration stop published

Hermes integrated review 154's exact accepted test correction in commit `3155293` and
pushed it. The required focused restart reached C3:

- C1 migration tests returned exit 0.
- C2 download atomicity tests returned exit 0.
- C3 Ruff returned exit 1 with five `F401` unused-import findings in
  `tests/acquisition/test_binance_usdm_harmonic_qualification.py`.

Commands C4-C5, migration preconditions, the migration-only invocation, ordinary resume,
sample acquisition, Gate 2, and later work were not run. CEX-002 remains `IN_PROGRESS`;
Gate 1 has not passed; next ticket remains `NONE`.

## Focused tests accepted - five-import Spark cleanup

Review 156 accepts Hermes's exact test integration and required C3 stop. C1 and C2 both
returned exit 0. Ruff's only findings are five `F401` imports for migration helpers that
the tests now access through the imported module object rather than direct names.

Implementation Dev - Codex Spark using GPT-5.3-Codex-Spark High is authorized only to
remove the five exact unused names enumerated in review 156 from the test import list.
Spark changes no other byte, runs no command or Git operation, and returns the exact test
hash with the unchanged 285-test count. Production, CLI, and test behavior remain frozen;
Hermes remains unauthorized pending reviewer source acceptance.

No migration invocation, sample acquisition, Gate 2, reduced scope, Nautilus, Harmonic
Trader, payoff, PAPER, LIVE, or next-ticket work is authorized. CEX-002 remains
`IN_PROGRESS`; Gate 1 has not passed; next ticket remains `NONE`.

## Ruff cleanup accepted - Hermes restart authorized

Review 157 accepts and freezes the exact five-import deletion at
`5d4b2e2c199b6826e9da6d6561381207644d33c119572995c7211d5cead1c6d4`. Production,
CLI, all 285 tests, and every behavioral assertion remain unchanged.

Jr Dev - Hermes is authorized for review 157's exact test integration and a complete
C1-C5 restart. Only after all five commands return exit 0 may Hermes perform review 151's
exact migration preconditions, one migration-only invocation, after-proof, and record 158
publication. Every failure stops later work; no retry, ordinary resume, second migration,
or sample acquisition is authorized.

No migration before all focused commands pass, sample acquisition, Gate 2, reduced scope,
Nautilus, Harmonic Trader, payoff, PAPER, LIVE, or next-ticket work is authorized. CEX-002
remains `IN_PROGRESS`; Gate 1 has not passed; next ticket remains `NONE`.

## Record-158 migration restart and invocation stop published

Hermes integrated review 157's exact accepted import cleanup in commit `21fb4ec` and
pushed it. The focused restart passed C1-C5. Hermes then ran exactly one reviewed
`--apply-reviewed-v4-migration-only` invocation. The invocation exited status 1 after 495
seconds because `fapi:exchangeInfo` failed all five bounded attempts with DNS resolution
failure for `https://fapi.binance.com/fapi/v1/exchangeInfo`.

No retry, ordinary resume, second migration command, sample acquisition, Gate 2, or later
work was run. No version-4 lock was installed and no amendment ledger was prepared. The
retry journal changed to record the failed attempts; accepted report, manifest detail,
lock, legacy ledger, sample checkpoint/progress, listing checkpoint, official metadata, and
retained raw tree remained byte-identical. CEX-002 remains `IN_PROGRESS`; Gate 1 has not
passed; next ticket remains `NONE`.

## Network failure accepted - one direct migration retry authorized

Review 159 accepts the exact cleanup integration, all five exit-0 focused commands, and
Hermes's required stop. The migration failed before the transaction because restricted-
sandbox DNS could not resolve the official FAPI endpoint. Preflight remains `not_started`;
the version-2 lock is unchanged and the amendment ledger is absent.

Jr Dev - Hermes is authorized to preserve the advanced retry journal, re-prove review
159's exact immutable state, obtain network permission before launch, and make exactly one
direct network-enabled migration-only invocation. Hermes does not rerun C1-C5 and does not
consume a preliminary sandboxed attempt. It publishes record 160 and stops after every
status. No ordinary resume, further retry, or sample acquisition is authorized.

No sample acquisition, Gate 2, reduced scope, Nautilus, Harmonic Trader, payoff, PAPER,
LIVE, or next-ticket work is authorized. CEX-002 remains `IN_PROGRESS`; Gate 1 has not
passed; next ticket remains `NONE`.

## Record-160 network-enabled migration retry published

Hermes re-proved review 159's accepted retry preconditions, obtained network permission,
and ran exactly one direct network-enabled `--apply-reviewed-v4-migration-only`
invocation. The command exited status 2 after 555 seconds, the expected terminal status
for successful migration with Gate 1 still blocked.

The migration installed the reviewed version-4 lock at plan digest
`2fb0e47a3666f0e87b35dd7fdd6ea26aa352e34acf8dfd5debf590409aecbbef`, preserved the
prior version-2 lock content-addressably, and created an empty prepared amendment ledger
bound to the installed lock. `download_authorized=false`; no samples were acquired.

No ordinary resume, further retry, second migration command, Gate 2, or later work was
run. The accepted report, manifest detail, legacy ledger, sample checkpoint/progress,
retry journal, sample plan, listing checkpoint, official metadata, and retained raw tree
remained unchanged. CEX-002 remains `IN_PROGRESS`; Gate 1 has not passed; next ticket
remains `NONE`.

## Version-4 migration accepted - bounded sample execution authorized

Review 161 accepts the exact network-enabled migration transaction and the installed
version-4 authority. The lock contains 84 new sample objects totaling 1,049,324 planned
bytes, 12 retained objects, 10 aliases, and no budget-blocked entry. The amendment ledger
is empty and bound to the reviewed lock and executing source/config.

Jr Dev - Hermes is authorized for review 161's exact preproof, content-addressed
preservation of the accepted report, one direct network-enabled ordinary qualification
invocation, complete after-proof, and record 162 publication. Every status stops; there is
no retry or second invocation. This is bounded Gate-1 source sampling, not historical bulk
acquisition.

No Gate 2, normalization, catalog publication, Nautilus, Harmonic Trader, payoff, PAPER,
LIVE, reduced scope, paid source, or next-ticket work is authorized. CEX-002 remains
`IN_PROGRESS`; Gate 1 has not passed; next ticket remains `NONE`.

## Record-162 bounded version-4 sample execution published

Hermes preserved the accepted report bytes content-addressably, obtained network
permission, and ran exactly one ordinary qualification invocation against the installed
version-4 lock. The command exited status 2 after 829 seconds: valid terminal report, Gate
1 still blocked.

The run wrote a changed report 62 at SHA-256
`53f8f93379cb55d66b6de062f1a6a85f4c9dd318f5b41cc047bff2f5feeaaf51` and manifest detail
compressed SHA-256 `64d0f74b8e4696c98d0f96423185fd961aba6c63348d12425e3ec364b888f113`.
The raw tree advanced by exactly the locked 84 new files / 1,049,324 bytes. The version-4
lock, preserved prior report, preserved prior lock, legacy ledger, listing checkpoint, and
retry journal remained byte-identical.

The amendment ledger records the full 1,049,324-byte planned charge under the
268,435,456-byte allowance, with 82 settled transfer entries and 2 outstanding
reservations totaling 203,853 bytes. No retry, second invocation, automatic resume, Gate 2,
or later work was run. CEX-002 remains `IN_PROGRESS`; Gate 1 has not passed; next ticket
remains `NONE`.

## Sample outcome accepted - Claude semantic and authority correction

Review 163 accepts Hermes's exact bounded run and required stop as honest blocking
evidence. It does not accept Gate 1. The two reserved quote files prove that authentic
empty and one-sided book states are being rejected as whole-file corruption. The product
matrix also conflates source qualification with final release coverage and evaluates the
membership product against an empty family set.

ADR-0020 section 4b now separates Gate-1 source blockers from later release blockers,
defines typed two-sided/one-sided/empty quote semantics, fixes membership coverage, and
requires an explicit one-shot version-4 source-authority advance before corrected ordinary
execution.

Sr Dev - Claude Build using Claude Opus 5 is authorized only for review 163's three-path
source/test correction and exact-hash return. Claude runs no command or Git operation.
Hermes remains unauthorized pending reviewer source acceptance.

No integration, live transaction, ordinary resume, Gate 1 acceptance, sizing, Gate 2,
bulk acquisition, Nautilus, Harmonic Trader, payoff, PAPER, LIVE, or next-ticket work is
authorized. CEX-002 remains `IN_PROGRESS`; Gate 1 has not passed; next ticket remains
`NONE`.

## Claude review-163 source outcome - rejected before integration

Review 164 rejects the exact 296-test three-path drop before integration. The production
module has invalid dataclass field ordering and cannot import. The reviewed transaction is
also unreachable from both exact fresh and ledger-advanced states, the CLI withholds its
required report path, and the correction route enters ordinary network/cache/checkpoint
work that review 163 forbids.

Qualified Coinalyze rows retain a blocking default, derived taker flow is absent from the
actual later-release list, the CLI omits that list, and the quote classifier adds a zero-
quantity rule not present in ADR-0020. The required successful, recovery, idempotence,
mixed-state, mutation-boundary, lineage, and accounting tests are absent.

Sr Dev - Claude Build using Claude Opus 5 is authorized only for review 164's bounded
correction in the same three Python paths. Claude runs no command or Git operation and
returns all three hashes plus the unique CEX test-function count. Hermes remains
unauthorized pending reviewer source acceptance.

No integration, live transaction, ordinary resume, Gate 1 acceptance, sizing, Gate 2,
bulk acquisition, Nautilus, Harmonic Trader, payoff, PAPER, LIVE, or next-ticket work is
authorized. CEX-002 remains `IN_PROGRESS`; Gate 1 has not passed; next ticket remains
`NONE`.

## Claude review-164 correction - authority residual rejected

Review 165 accepts and freezes the corrected quote, membership, source/release, Coinalyze,
derived-flow, and CLI regions, but rejects the source-authority transaction before
integration. Its complete-state proof compares checkpoint-envelope fields against a lock
body that cannot contain them, so a fresh run mutates the ledger and lock and then fails.

The transaction also accepts caller-selected retained-evidence roots, incompletely proves
partial ledger and complete lock transforms, and overwrites a corrupt prior-ledger content
address. The recovery test removes all fixture authority constants before its retry, and
the accounting tests use an empty migrated ledger rather than preserving nonempty settled
charges and reservations.

Sr Dev - Claude Build using Claude Opus 5 is authorized only for review 165's two-path
production/test residual. The accepted CLI is frozen at SHA-256
`473185ca946dcc37d506d8891e8f955708ff80c976a586967762c1294956d28f`.
Claude runs no command or Git operation and returns both changed hashes, the unchanged CLI
hash, and the unique CEX test-function count. Hermes remains unauthorized.

No integration, live transaction, ordinary resume, Gate 1 acceptance, sizing, Gate 2,
bulk acquisition, Nautilus, Harmonic Trader, payoff, PAPER, LIVE, or next-ticket work is
authorized. CEX-002 remains `IN_PROGRESS`; Gate 1 has not passed; next ticket remains
`NONE`.

## Claude authority production accepted - Spark test correction

Review 166 accepts and freezes the production source-authority transaction at
`bed5ab4a9d18ed0cb7410d8efc58b6a6fdb88153a68c03ae409494358d48fac7` and retains the
accepted CLI at
`473185ca946dcc37d506d8891e8f955708ff80c976a586967762c1294956d28f`.

The 305-test path is rejected only because its accepted-state fixture searches for an
uncharged download after the synthetic plan has settled every download, and its
altered-accounting branch reserves an already-accounted key and therefore changes nothing.
The existing rejected-state tests also need the explicit public-apply snapshot assertions
specified in review 166.

Implementation Dev - Codex Spark using GPT-5.3-Codex-Spark High is authorized only for
review 166's exact mechanical correction in
`tests/acquisition/test_binance_usdm_harmonic_qualification.py`. Spark changes no
production/CLI byte, adds no test, preserves the 305-test count, runs no command or Git
operation, and returns the exact test hash. Hermes remains unauthorized pending reviewer
source acceptance.

No integration, live transaction, ordinary resume, Gate 1 acceptance, sizing, Gate 2,
bulk acquisition, Nautilus, Harmonic Trader, payoff, PAPER, LIVE, or next-ticket work is
authorized. CEX-002 remains `IN_PROGRESS`; Gate 1 has not passed; next ticket remains
`NONE`.

## Authority source accepted - Hermes integration only

Review 167 accepts and freezes the complete three-path source drop at production
`bed5ab4a9d18ed0cb7410d8efc58b6a6fdb88153a68c03ae409494358d48fac7`, CLI
`473185ca946dcc37d506d8891e8f955708ff80c976a586967762c1294956d28f`, and 305-test
source `4a9602d7247c0b211dd21925f724ec5e22d529646b71c77cbd529ad7d59a9fef`.

Jr Dev - Hermes is authorized only for review 167's exact three-path integration,
stop-on-first-failure five-command sequence, and record 168 publication. The live
source-authority transaction is a separate reviewer gate and remains unauthorized.

No live transaction, data or source-data network operation beyond the authorized Git
pushes, ordinary qualification, Gate 1
acceptance, sizing, Gate 2, bulk acquisition, Nautilus, Harmonic Trader, payoff, PAPER,
LIVE, or next-ticket work is authorized. CEX-002 remains `IN_PROGRESS`; Gate 1 has not
passed; next ticket remains `NONE`.

## Record-168 authority source integration stop published

Hermes integrated review 167's exact three accepted Python paths in commit `1e62cd8` and
pushed it. The focused sequence stopped at C1:

`.venv/bin/python -m pytest tests/acquisition/test_binance_usdm_harmonic_qualification.py -q --tb=short`

C1 exited status 2 during collection because
`src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` references
`COST_OBSERVATION_PRICEABLE` while defining `CostSampleValidation` before that name is
defined.

Commands C2-C5 were not run. No live source-authority transaction, data mutation,
ordinary qualification, Gate 1 acceptance, Gate 2, or later work was run. CEX-002 remains
`IN_PROGRESS`; Gate 1 has not passed; next ticket remains `NONE`.

## Authority import failure - Spark constant-order correction

Review 169 accepts Hermes's exact integration and required C1 stop. C1 could not collect
because `CostSampleValidation` evaluates `COST_OBSERVATION_PRICEABLE` before the module
declares that constant. CLI and tests remain accepted and frozen.

Implementation Dev - Codex Spark using GPT-5.3-Codex-Spark High is authorized only to move
the unchanged quote-state/cost-observation constant block above `CostSampleValidation` in
the production module, leaving no duplicate and changing no other byte. Spark runs no
command or Git operation and returns the production hash plus confirmation of the frozen
CLI/test hashes and unchanged 305-test count. Hermes remains unauthorized.

No integration, live transaction, data or source-data network operation, ordinary
qualification, Gate 1 acceptance, sizing, Gate 2, bulk acquisition, Nautilus, Harmonic
Trader, payoff, PAPER, LIVE, or next-ticket work is authorized. CEX-002 remains
`IN_PROGRESS`; Gate 1 has not passed; next ticket remains `NONE`.

## Authority import correction accepted - Hermes restart

Review 170 accepts and freezes the corrected production module at
`068763e2359abf4fc4fe4b7e7fdea95495db5c22bf362d468fec4056775ecb7e`. The CLI remains
`473185ca946dcc37d506d8891e8f955708ff80c976a586967762c1294956d28f`; the 305-test path
remains `4a9602d7247c0b211dd21925f724ec5e22d529646b71c77cbd529ad7d59a9fef`.

Jr Dev - Hermes is authorized only for the exact one-path production integration, a
complete C1-C5 restart, and record 171 publication specified in review 170. The first
failure stops later commands. The live source-authority transaction remains unauthorized.

No live transaction, data or source-data network operation beyond authorized Git pushes,
ordinary qualification, Gate 1 acceptance, sizing, Gate 2, bulk acquisition, Nautilus,
Harmonic Trader, payoff, PAPER, LIVE, or next-ticket work is authorized. CEX-002 remains
`IN_PROGRESS`; Gate 1 has not passed; next ticket remains `NONE`.

## Record-174 authority test integration passed

Hermes integrated review 173's exact accepted test path in commit `7538559` and pushed it.
`HEAD == origin/main` after the push.

The complete focused restart passed:

- C1 `.venv/bin/python -m pytest tests/acquisition/test_binance_usdm_harmonic_qualification.py -q --tb=short` exited 0 in 6 seconds.
- C2 `.venv/bin/python -m pytest tests/test_download_atomicity.py -q --tb=short` exited 0 in 0 seconds.
- C3 `.venv/bin/python -m ruff check src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py scripts/research/qualify_binance_usdm_harmonic_sources.py tests/acquisition/test_binance_usdm_harmonic_qualification.py tests/test_download_atomicity.py` exited 0 in 0 seconds.
- C4 `python3 scripts/check_repo_control.py` exited 0 in 0 seconds.
- C5 `git diff --check` exited 0 in 0 seconds.

Final hashes remain production
`068763e2359abf4fc4fe4b7e7fdea95495db5c22bf362d468fec4056775ecb7e`, CLI
`473185ca946dcc37d506d8891e8f955708ff80c976a586967762c1294956d28f`, and test
`4cf2b786e95723f933a293b8bfdfb59236cfad8490ec7afcbadecc347e543ff0`; test count remains
305.

No live source-authority transaction, data mutation, ordinary qualification, Gate 1
acceptance, Gate 2, or later work was run. CEX-002 remains `IN_PROGRESS`; Gate 1 has not
passed; next ticket remains `NONE`.

## Record-171 authority import integration stop published

Hermes integrated review 170's exact accepted production path in commit `c4a3df4` and
pushed it. The focused restart stopped at C1:

`.venv/bin/python -m pytest tests/acquisition/test_binance_usdm_harmonic_qualification.py -q --tb=short`

C1 exited status 1 after reaching `[100%]` with five failed tests: one accepted-check name
mismatch, two quote-validation message mismatches, one all-empty cost-object key ordering
mismatch, and one CLI source assertion expecting
`reviewed_source_correction_preflight(`.

Commands C2-C5 were not run. No live source-authority transaction, data mutation,
ordinary qualification, Gate 1 acceptance, Gate 2, or later work was run. CEX-002 remains
`IN_PROGRESS`; Gate 1 has not passed; next ticket remains `NONE`.

## Focused authority failures - Spark assertions only

Review 172 accepts the import correction and Hermes's exact C1 stop. Production remains
frozen at `068763e2359abf4fc4fe4b7e7fdea95495db5c22bf362d468fec4056775ecb7e`; CLI remains
frozen at `473185ca946dcc37d506d8891e8f955708ff80c976a586967762c1294956d28f`.

C1's five failures are confined to stale check/message assertions, an incorrect ordering
comparison between two exact cost-sample views, and an obsolete assertion that the CLI
calls an internally encapsulated preflight directly. Implementation Dev - Codex Spark
using GPT-5.3-Codex-Spark High is authorized only for review 172's exact five assertion
corrections in the CEX test path. Spark changes no other byte, adds no test, preserves the
305-test count, runs no command or Git operation, and returns the test hash. Hermes remains
unauthorized.

No integration, live transaction, data or source-data network operation, ordinary
qualification, Gate 1 acceptance, sizing, Gate 2, bulk acquisition, Nautilus, Harmonic
Trader, payoff, PAPER, LIVE, or next-ticket work is authorized. CEX-002 remains
`IN_PROGRESS`; Gate 1 has not passed; next ticket remains `NONE`.

## Authority test assertions accepted - Hermes restart

Review 173 accepts and freezes the test path at
`4cf2b786e95723f933a293b8bfdfb59236cfad8490ec7afcbadecc347e543ff0`. Production remains
`068763e2359abf4fc4fe4b7e7fdea95495db5c22bf362d468fec4056775ecb7e`; CLI remains
`473185ca946dcc37d506d8891e8f955708ff80c976a586967762c1294956d28f`; the test count
remains 305.

Jr Dev - Hermes is authorized only for the exact test-path integration, a complete C1-C5
restart, and record 174 publication specified in review 173. The first failure stops later
commands. The live source-authority transaction remains unauthorized.

No live transaction, data or source-data network operation beyond authorized Git pushes,
ordinary qualification, Gate 1 acceptance, sizing, Gate 2, bulk acquisition, Nautilus,
Harmonic Trader, payoff, PAPER, LIVE, or next-ticket work is authorized. CEX-002 remains
`IN_PROGRESS`; Gate 1 has not passed; next ticket remains `NONE`.

## Authority tests passed - one local transaction authorized

Review 175 accepts Hermes's exact test integration and complete exit-zero C1-C5 sequence.
The live store remains in the exact fresh state pinned by ADR-0020 section 4b.

Jr Dev - Hermes is authorized only for review 175's exact preproof, one local
`--apply-reviewed-v4-source-correction-only` invocation, after-proof, and record 176
publication. Any nonzero result stops without retry or recovery. Ordinary qualification
remains a separate unauthorized gate.

No network call, report write, sample acquisition, reservation reconciliation, ordinary
qualification, Gate-1 acceptance, sizing, Gate 2, bulk acquisition, Nautilus, Harmonic
Trader, payoff, PAPER, LIVE, or next-ticket work is authorized. CEX-002 remains
`IN_PROGRESS`; Gate 1 has not passed; next ticket remains `NONE`.

## Record-176 authority transaction execution published

Hermes executed review 175's single local
`--apply-reviewed-v4-source-correction-only` invocation. It exited status 0 and reported
`transaction=cex002_reviewed_v4_source_correction`, `executed=true`, and
`state=source_identity_advanced`.

The live lock advanced to
`522271238e38a3652f9521b236981544782e02459450703f21e9ef344d476fa6`; the live amendment
ledger advanced to `832228fd2b4b9394e205a69441281ddbfccc92c227144c5c0c2b8181e164e488`.
The prior lock and prior amendment ledger now exist at their required content-addressed
evidence paths and rehash to
`8fda3c7db11173dafa122114667622f501b62ecf05f12cdf796897d5af0942bc` and
`2a4c4db6e14350d6814b6f72a3caa1357659cd064a13fd2edeb84a2896223c8c`.

Plan version 4 and digest
`2fb0e47a3666f0e87b35dd7fdd6ea26aa352e34acf8dfd5debf590409aecbbef` remain exact.
Accounting remains 82 charges, 845,471 transferred bytes, 1,049,324 charged bytes, two
reservations, 203,853 planned reservation bytes, 268,435,456-byte allowance, zero acquired
samples, zero reconciled reservations, and `download_authorized=false`.

The report, legacy ledger, sample plan, retry journal, listing checkpoint, official
metadata, raw tree, list cache, FAPI caches, Coinalyze cache, prior-report tree, and
manifest tree remained byte-identical to the pre-snapshot. No `.env` file was loaded. No
network permission, retry, recovery, ordinary qualification, report write, sample
acquisition, reservation reconciliation, Gate 1 acceptance, Gate 2, or later work was run.
CEX-002 remains `IN_PROGRESS`; Gate 1 has not passed; next ticket remains `NONE`.

## Authority transaction accepted - corrected qualification authorized

Review 177 accepts the exact source-authority transaction. Review 175's phrase "exactly
one source receipt exists" is corrected to two total receipts, exactly one appended by
the correction; record 176 and the live authority are architecture-correct.

Jr Dev - Hermes is authorized only for review 177's exact preproof, collision-safe report
preservation, one network-enabled corrected ordinary qualification invocation, complete
after-proof, and record 178 publication. Every terminal status stops further execution.
Reviewer inspection remains required before Gate 1 can be accepted.

No second invocation, source correction, migration, candidate construction, full-history
or bulk acquisition, Gate 1 acceptance, Gate 2, normalization, catalog publication,
Nautilus, Harmonic Trader, payoff, PAPER, LIVE, or next-ticket work is authorized.
CEX-002 remains `IN_PROGRESS`; Gate 1 has not passed; next ticket remains `NONE`.

## Record-178 corrected qualification execution published

Hermes executed review 177's single network-enabled ordinary qualification run. It exited
status 0 after 592 seconds and wrote a changed valid report at
`research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json`.

The report identity is
`bf01f88976e2ac3d224e843f340de726f5c8c337ba56a50f9e3c6f75c4d6f227` with size
13,559,766 bytes. It claims `gate_status=QUALIFIED`, `accepted=true`, no source-blocked
products, seven release-blocked products, 11 product-matrix rows, 106 reused samples, zero
acquired samples, and a new manifest detail at
`evidence/manifests/sha256/1d21de4d68fb0dfd330dc480a0d27ddf2216c3b7d5e93b13ff70ea26230f968d.jsonl.gz`
with compressed hash `576b3d7b03ff16fd492c5a9382e35f65e54d73ef3996c3a7fe5c6e6ba49b0fb4`.

The accepted prior report was preserved content-addressably at
`data/cex002_qualify/evidence/prior_reports/sha256/53f8f93379cb55d66b6de062f1a6a85f4c9dd318f5b41cc047bff2f5feeaaf51.json`.
The raw tree and list cache stayed byte-identical. The two prior reservations settled in
the amendment ledger; the ledger now has 84 charges, zero reservations, and 1,049,324
transferred/charged bytes. The corrected authority binding and two source receipts remain
exact.

Gate 1 is not accepted by Hermes. Reviewer inspection of record 178 and report 62 remains
mandatory. No second invocation, retry, source correction, migration, candidate
construction, bulk acquisition, Gate 1 acceptance, Gate 2, or later work was run. CEX-002
remains `IN_PROGRESS`; Gate 1 has not passed; next ticket remains `NONE`.

## Gate 1 accepted - bounded storage-sizing source authorized

Review 179 accepts Gate 1 at report-62 SHA-256
`bf01f88976e2ac3d224e843f340de726f5c8c337ba56a50f9e3c6f75c4d6f227` and reviewed
commit `dea14dcd7606bd4fb01d035e7440d0b15f2b4abd`. All nine source-gated products are
qualified against real declared sources with no source blocker. Seven products remain
honestly release-blocked pending full acquisition/publication; no later gate has passed.

ADR-0021 defines the missing full-universe storage-sizing method. The exact Binance raw
component is 20,351,715,427 projected new bytes, but total capacity remains unknown until
the local lossless-envelope sizing includes full supported Coinalyze liquidation receipts,
normalized/catalog allocation, immutable-publication high-water, and operating reserve.

Sr Dev - Claude Build using Claude Opus 5 is authorized only to author the three new
sizing production/CLI/test paths enumerated in review 179. Claude runs no test, linter,
control, Git, network, sizing, acquisition, or data command; edits no existing path, data,
or repository record; returns the three hashes and test count; and stops for reviewer
inspection. Hermes remains unauthorized.

No sizing execution, Gate 2 acceptance, bulk acquisition, normalization, catalog
publication, NautilusTrader, Harmonic Trader, payoff, PAPER, LIVE, paid source, reduced
scope, or next-ticket work is authorized. CEX-002 remains `IN_PROGRESS`; Gate 1 is
accepted; next ticket remains `NONE`.

## Claude sizing source rejected - bounded senior correction

Review 181 rejects Claude's three-path sizing drop. Scope was correct, but the source
cannot run against the accepted store and can materially understate capacity: it omits
the separate 3,144-object, 12,522,974,218-byte cost manifest; accepts caller-created
Coinalyze lifecycle/response authority; substitutes a floating-point-selected Binance
ratio for a Coinalyze envelope; and miscomputes symbol-month partitions and high-water.
Envelope measurement, durable receipt identity/publication, and the synthetic tests also
violate review 179.

Sr Dev - Claude Build using Claude Opus 5 is authorized only to correct the same exact
three untracked sizing paths under review 181. Claude runs no test, linter, control, Git,
network, sizing, acquisition, or data command; changes no other path, record, or data;
returns three hashes and the corrected test-function count; and stops for reviewer
inspection. Hermes remains unauthorized.

Gate 1 remains accepted. No integration, sizing execution, Gate 2 acceptance, bulk
acquisition, normalization, catalog publication, NautilusTrader, Harmonic Trader, payoff,
PAPER, LIVE, paid source, reduced scope, or next-ticket work is authorized. CEX-002
remains `IN_PROGRESS`; next ticket remains `NONE`.

## Claude sizing correction rejected - final surgical correction

Review 182 rejects Claude's corrected three-path sizing drop. The rewrite closes the
separate cost-manifest, report-bound Coinalyze, exact-rational envelope, grouping, fixed
CLI target, and basic collision-publication defects, but the real invocation still cannot
complete. It counts the 96 sizing samples as acquisition credit although report 62 proves
a separate 73-object, 5,225,416-byte consumable set; the synthetic fixture explicitly
masks that distinction.

The source also labels gross liquidation bytes as new Coinalyze raw while omitting the
inventory/retained-credit equation, counts five qualification evidence responses instead
of projected acquisition receipts for catalog overhead, undercounts the final receipt,
and cannot reproduce the fixed receipt on rerun. Largest-partition high-water combines
multiple logical outputs; source division contradicts its own integer guard; and
publication still lacks streaming and complete no-follow behavior.

Sr Dev - Claude Build using Claude Opus 5 is authorized only for review 182's final
surgical correction of the same three untracked sizing paths. Claude preserves all
accepted review-181 corrections, closes the six exact review-182 findings, runs no test,
linter, control, Git, network, sizing, acquisition, or data command, edits no other path,
and returns three hashes plus the corrected test-function count. Hermes remains
unauthorized.

Gate 1 remains accepted. No integration, sizing execution, Gate 2 acceptance, bulk
acquisition, normalization, catalog publication, NautilusTrader, Harmonic Trader, payoff,
PAPER, LIVE, paid source, reduced scope, or next-ticket work is authorized. CEX-002
remains `IN_PROGRESS`; next ticket remains `NONE`.

## Claude sizing residual review - narrow correction

Review 183 rejects the review-182 correction. It successfully separates the real
73-object acquisition credit from the 96-sample coefficient cohort and corrects production
partition fan-out, integer conversion, projected catalog receipts, exact receipt length,
and streaming copies. Four residuals remain.

Coinalyze still models the one retained two-symbol liquidation response as two synthetic
receipts, omits the exact retained inventory bytes, and does not prove timestamp coverage.
The fixed-target rerun still collides when available space changes above the reserve floor,
and prior validation omits material receipt sections. One older test contradicts the
corrected partition implementation. Publication checks still have pathname race windows
and the tests do not simulate a symlink swap or actual race.

Sr Dev - Claude Build using Claude Opus 5 is authorized only for review 183's four-finding
correction in the same exact three untracked paths. Claude preserves all accepted prior
corrections, runs no test, linter, control, Git, network, sizing, acquisition, or data
command, edits no other path, and returns three hashes plus test-function count. Hermes
remains unauthorized.

Gate 1 remains accepted. No integration, sizing execution, Gate 2 acceptance, bulk
acquisition, normalization, catalog publication, NautilusTrader, Harmonic Trader, payoff,
PAPER, LIVE, paid source, reduced scope, or next-ticket work is authorized. CEX-002
remains `IN_PROGRESS`; next ticket remains `NONE`.

## Storage-sizing source accepted - integration and real sizing authorized

Review 184 accepts Claude's review-183 correction at production SHA-256
`795eab0312064e3d7be7dd8f826b5dc5754a8e6b5e702872ac3699dad1532390`, unchanged CLI
SHA-256 `78ee687c734fc94070952d290752acdbd007970fb26c616e5e6845f1de3702ad`, and 44-test
SHA-256 `e7127f9724ce046233979ec29d43035ff5358c213beee2b9cd22b0e841ee323a`.
The four review-183 residuals are closed. No further static source-correction cycle is
authorized.

Jr Dev - Hermes is authorized only for review 184's exact three-path integration, focused
44-test run, exact-path lint and control check, followed conditionally by exactly two
local credential-free sizing invocations: first publication and identical fixed-target
reproof. Hermes publishes record 185, the real receipt if created, and the matching
control-plane transition, commits and pushes only the enumerated CEX-002 paths, and stops
for reviewer inspection. The first nonzero command stops all later work.

Gate 1 remains accepted. Gate 2 remains unaccepted until the reviewer inspects the real
receipt and record 185. No network call, qualification, bulk acquisition, normalization,
catalog publication, NautilusTrader, Harmonic Trader, payoff, PAPER, LIVE, paid source,
reduced scope, or next-ticket work is authorized. CEX-002 remains `IN_PROGRESS`; next
ticket remains `NONE`.

## Record-185 storage-sizing integration stop published

Hermes integrated review 184's exact three accepted sizing paths. The focused sizing test
command stopped the sequence:

`.venv/bin/python -m pytest tests/acquisition/test_binance_usdm_harmonic_sizing.py -q --tb=short`

It exited status 1 in 3 seconds. The primary setup error was
`TypeError: open() got an unexpected keyword argument 'mtime'` at the test fixture call
`gzip.open(..., mtime=0)`. Pytest also reported direct `SizingError` failures in retained
sample validation, rational/reserve validation, and receipt/envelope publication tests.

Per review 184, Hermes ran no ruff command, no review-184 control command, and no sizing
invocation. `research/sprint_004/180_CEX002_GATE2_STORAGE_SIZING.json` and
`data/cex002_qualify/evidence/sizing/v1/envelopes/sha256` remain absent. Gate 1 remains
accepted. Gate 2 remains unaccepted. Next ticket remains `NONE`.

## Record 185 reviewed - mechanical test correction authorized

Review 186 accepts Hermes's exact stop and proves the failure is confined to two test
source mistakes. `gzip.open()` does not accept the fixture's `mtime` argument, causing 37
setup errors. The first direct test then reloads the sizing module and replaces its
`SizingError` class while the test module retains the old imported class, causing 16
otherwise-expected exceptions to escape `pytest.raises`.

Implementation Dev - Codex Spark using GPT-5.3-Codex-Spark High is authorized only to
replace the gzip writer with deterministic `gzip.GzipFile`, remove the destructive module
reload, and point the literal-pin assertions at the existing module. Spark edits only the
tracked sizing test path, preserves all cases and the 44-test count, runs no command or Git
operation, returns the test SHA-256, and stops for reviewer inspection. Production and CLI
remain frozen at their review-184 hashes. Hermes restart remains unauthorized.

Gate 1 remains accepted. Gate 2 remains unaccepted. No sizing invocation, network,
qualification, bulk acquisition, normalization, catalog publication, NautilusTrader,
Harmonic Trader, payoff, PAPER, LIVE, paid source, reduced scope, or next-ticket work is
authorized. CEX-002 remains `IN_PROGRESS`; next ticket remains `NONE`.

## Storage-sizing test correction accepted - Hermes restart authorized

Review 187 accepts Spark's exact one-file correction at test SHA-256
`e7b7103cb36f83642762a91101be98ae368ba41b425f8a3e00711632895da6de` with 44 test
functions. The deterministic fixture now uses `gzip.GzipFile`, the destructive module
reload is absent, and production/CLI remain frozen at their review-184 identities.

Jr Dev - Hermes is authorized only to integrate that exact test diff and restart the
review-184 sequence from focused tests. The first nonzero result stops. If focused tests,
exact-path lint, and control all pass, Hermes runs the exact local sizing command once,
proves the receipt/envelope publication, runs it exactly once more for byte-identical
reproof, publishes record 188 and receipt 180 if created, commits/pushes only the
enumerated CEX-002 paths, and stops for reviewer inspection.

Gate 1 remains accepted. Gate 2 remains unaccepted until reviewer inspection of a real
receipt. No network, qualification, bulk acquisition, normalization, catalog publication,
NautilusTrader, Harmonic Trader, payoff, PAPER, LIVE, paid source, reduced scope, or
next-ticket work is authorized. CEX-002 remains `IN_PROGRESS`; next ticket remains `NONE`.

## Record-188 storage-sizing restart stop published

Hermes integrated review 187's accepted one-file sizing-test correction and restarted the
review-184 sequence from the focused sizing tests:

`.venv/bin/python -m pytest tests/acquisition/test_binance_usdm_harmonic_sizing.py -q --tb=short`

It exited status 1 in 2 seconds. Pytest reported 18 failed tests. The dominant failure was
`SizingError: the cohort does not cover every physical family`, with missing physical
families including daily and monthly premium/mark/index kline families, monthly klines,
monthly funding rate, and daily book depth. Additional failures involved the static
rational-comparison source scan and two publication-error expectation mismatches.

Per review 187, Hermes ran no ruff command, no review-187 control command, and no sizing
invocation. `research/sprint_004/180_CEX002_GATE2_STORAGE_SIZING.json` and
`data/cex002_qualify/evidence/sizing/v1/envelopes/sha256` remain absent. Gate 1 remains
accepted. Gate 2 remains unaccepted. Next ticket remains `NONE`.

## Record 188 reviewed - bounded test correction authorized

Review 189 accepts Hermes's exact stop and classifies all observed failures as test-source
defects. The fixture selects the first rows rather than one non-consumable sample from each
of 12 physical families; the arithmetic test scans unrelated path-join syntax; and the
symlink test omits production's equally safe confinement error.

Implementation Dev - Codex Spark using GPT-5.3-Codex-Spark High is authorized only for
review 189's three exact corrections in the tracked sizing test path. Spark preserves all
44 test functions, runs no command or Git operation, changes no production/CLI byte,
returns the test SHA-256, and stops for reviewer inspection. Hermes restart remains
unauthorized.

Gate 1 remains accepted. Gate 2 remains unaccepted. No sizing invocation, network,
qualification, bulk acquisition, normalization, catalog publication, NautilusTrader,
Harmonic Trader, payoff, PAPER, LIVE, paid source, reduced scope, or next-ticket work is
authorized. CEX-002 remains `IN_PROGRESS`; next ticket remains `NONE`.

## Spark sizing-test correction rejected - final mechanical correction

Review 190 accepts the corrected 12-family non-consumable cohort and focused arithmetic
scan but rejects the test drop at SHA-256
`ee556f77d860bc9c439221254203143d6baffbc5d36ef468f57e9430d5651aaa`. One now-reachable
end-to-end assertion uses the nonexistent `coinalyze_receipts` field instead of
`projected_coinalyze_receipts`; the no-float scan skips rather than rejects `float(`; and
two unrelated symlink regexes were broadened beyond review 189.

Implementation Dev - Codex Spark using GPT-5.3-Codex-Spark High is authorized only for
review 190's four exact mechanical corrections in the tracked sizing test path, including
100-column wrapping. Spark preserves all 44 tests, runs no command or Git operation,
changes no production/CLI byte, returns the test SHA-256, and stops for reviewer
inspection. Hermes restart remains unauthorized.

Gate 1 remains accepted. Gate 2 remains unaccepted. No sizing invocation, network,
qualification, bulk acquisition, normalization, catalog publication, NautilusTrader,
Harmonic Trader, payoff, PAPER, LIVE, paid source, reduced scope, or next-ticket work is
authorized. CEX-002 remains `IN_PROGRESS`; next ticket remains `NONE`.

## Final sizing-test correction accepted - Hermes restart authorized

Review 191 accepts Spark's final test-only correction at SHA-256
`585f20db0461ad92af7cf6b1d4143aa52c4dfdff5f2bbfa44e76d4f6334e9f96`, preserving 44
test functions and the frozen production/CLI identities. No further Spark work is
authorized.

Jr Dev - Hermes is authorized only to integrate that exact test diff and restart focused
tests, exact-path lint, and control. The first nonzero result stops. If all three pass,
Hermes runs exactly two local sizing invocations for first publication and byte-identical
reproof, publishes record 192 and receipt 180 if created, updates the control plane,
commits/pushes only the enumerated CEX-002 paths, and stops for reviewer inspection.

Gate 1 remains accepted. Gate 2 remains unaccepted until reviewer inspection of a real
receipt. No network, qualification, bulk acquisition, normalization, catalog publication,
NautilusTrader, Harmonic Trader, payoff, PAPER, LIVE, paid source, reduced scope, or
next-ticket work is authorized. CEX-002 remains `IN_PROGRESS`; next ticket remains `NONE`.

## Record-192 storage-sizing final restart stop published

Hermes integrated review 191's accepted one-file sizing-test correction and restarted the
verification sequence. The focused sizing tests passed:

`.venv/bin/python -m pytest tests/acquisition/test_binance_usdm_harmonic_sizing.py -q --tb=short`

It exited status 0 in 2 seconds. The next required exact-path ruff command failed:

`.venv/bin/python -m ruff check src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py scripts/research/size_binance_usdm_harmonic_release.py tests/acquisition/test_binance_usdm_harmonic_sizing.py`

It exited status 1 in 1 second with three `F401` unused imports in
`tests/acquisition/test_binance_usdm_harmonic_sizing.py`: `SIZING_ROW_BATCH`,
`family_coefficients`, and `verify_retained_sample`.

Per review 191, Hermes ran no repo-control command and no sizing invocation.
`research/sprint_004/180_CEX002_GATE2_STORAGE_SIZING.json` and
`data/cex002_qualify/evidence/sizing/v1/envelopes/sha256` remain absent. Gate 1 remains
accepted. Gate 2 remains unaccepted. Next ticket remains `NONE`.

## Record 192 reviewed - exact three-import correction

Review 193 accepts the 74-case focused test pass and Hermes's required Ruff stop. The only
Ruff findings are three unused direct imports in the sizing test path:
`SIZING_ROW_BATCH`, `family_coefficients`, and `verify_retained_sample`.

To conserve Spark usage, Sr Dev - Claude Build using Claude Opus 5 is authorized only to
delete those exact three import lines. Claude changes no other byte, reads no other path,
runs no command or Git operation, preserves all 44 test functions, returns the test hash,
and stops for reviewer inspection. Hermes remains unauthorized.

Gate 1 remains accepted. Gate 2 remains unaccepted. No sizing invocation, network,
qualification, bulk acquisition, normalization, catalog publication, NautilusTrader,
Harmonic Trader, payoff, PAPER, LIVE, paid source, reduced scope, or next-ticket work is
authorized. CEX-002 remains `IN_PROGRESS`; next ticket remains `NONE`.

## Ruff correction accepted - Hermes verification and sizing restart

Review 194 accepts Claude's exact three-import deletion at test SHA-256
`fda45c767e8cf271136f2a25769e37f64c57428fde15e508d0045b975679b2c7`, preserving 44
test functions and the frozen production/CLI identities.

Jr Dev - Hermes is authorized only to integrate that exact test diff, restart focused
tests, exact-path Ruff, and control, then conditionally run exactly two local sizing
invocations for first publication and byte-identical reproof. The first nonzero result
stops. Hermes publishes record 195 and receipt 180 if created, updates the control plane,
commits/pushes only the enumerated CEX-002 paths, and stops for reviewer inspection.

Gate 1 remains accepted. Gate 2 remains unaccepted until reviewer inspection of a real
receipt. No network, qualification, bulk acquisition, normalization, catalog publication,
NautilusTrader, Harmonic Trader, payoff, PAPER, LIVE, paid source, reduced scope, or
next-ticket work is authorized. CEX-002 remains `IN_PROGRESS`; next ticket remains `NONE`.

## Record-195 storage-sizing verification and execution stop published

Hermes integrated review 194's accepted three-import test cleanup and ran the authorized
stop-on-first-failure sequence. Focused sizing tests passed in 2 seconds, exact-path Ruff
passed, and repository control passed in 1 second.

The first authorized local sizing invocation then failed:

`.venv/bin/python scripts/research/size_binance_usdm_harmonic_release.py --manifest-detail-path data/cex002_qualify/evidence/manifests/sha256/1d21de4d68fb0dfd330dc480a0d27ddf2216c3b7d5e93b13ff70ea26230f968d.jsonl.gz`

It exited status 1 in 167 seconds with:

`ERROR: accepted sizing authority does not match its pinned identity`

Per review 194, Hermes did not run the second sizing invocation. Receipt 180 and the
content-addressed sizing-envelope tree remain absent. Gate 1 remains accepted. Gate 2
remains unaccepted. Next ticket remains `NONE`.

## Record 195 accepted - path-bound authority correction

Review 196 accepts Hermes's stop and identifies the exact failure. The sizing proof uses
only 73 manifest-consumable keys totaling 763,304 retained bytes, while report 62's valid
deduplicated selected-plus-cost authority remains 73 unique blobs totaling 5,225,416
bytes.

ADR-0022 finds 17 basename-only recovered Kline mappings that are not full-key authority.
They duplicate valid fresh digests and therefore add no byte credit, but they falsely mark
17 selected-manifest keys consumable. The 96-object Gate-1 cohort contains none of those
substitutions, so the source finding remains accepted; report 62's affected publication
authority is suspended for sizing and acquisition until corrected and superseded.

Sr Dev - Claude Build is authorized only to implement ADR-0022 in the qualification source
and its test source per review 196, return both hashes and the test count, and stop. No
command execution, Git, repository-record edit, data mutation, sizing edit, or sizing retry
is authorized. Gate 2 remains unaccepted; next ticket remains `NONE`.

## ADR-0022 source drop rejected - exact correction

Review 197 rejects Claude's first ADR-0022 drop. The domain rule rejects multiple matches
but still accepts a persisted recovered key with zero domain matches. Rejected rows also
re-enter through raw checkpoint consumers in plan execution, acquisition reuse, retained
snapshots, ledger accounting, and credit. Existing direct-lookup tests were not migrated
to the new required domain binding, and the new helper-only test does not prove production
exclusion.

Sr Dev - Claude Build is authorized only to correct the same qualification source/test
paths: require exact-singleton full-key binding, use one effective checkpoint authority
through every consumer, fail closed if execution would require rejected lineage, migrate
affected existing tests, and add the integration and real dedup proofs in review 197.
Claude returns hashes/count and stops without commands, data, Git, records, sizing edits,
or a sizing retry. Hermes remains unauthorized. Gate 2 remains unaccepted; next ticket
remains `NONE`.

## Record-204 path-bound recovery integration stop published

Hermes integrated review 203's accepted ADR-0022 qualification source and test files.
The required qualification-module test command failed:

`.venv/bin/python -m pytest tests/acquisition/test_binance_usdm_harmonic_qualification.py -q --tb=short`

It exited status 1 in 7 seconds. The single failure was
`test_migration_does_not_adopt_a_recoverable_missing_checkpoint_entry`, which raised
`StopIteration` at `tests/acquisition/test_binance_usdm_harmonic_qualification.py:9339`.

Per review 203, exact-path Ruff was skipped after the first nonzero command. Hermes
published record 204, ran repo-control and path-restricted whitespace validation, and
stopped for reviewer inspection. No qualification, authority mutation, sizing retry,
acquisition, normalization, catalog publication, NautilusTrader, Harmonic Trader, payoff,
PAPER, LIVE, paid source, reduced scope, or next-ticket work was run. Gate 2 remains
unaccepted. Next ticket remains `NONE`.

## Record-204 failure accepted; one test fixture correction required

Review 205 accepts Hermes's five-path integration commit and record 204 as accurate
failure evidence. The focused suite's sole failure is a test-fixture defect:
`test_migration_does_not_adopt_a_recoverable_missing_checkpoint_entry` searches the
monthly/daily Kline fixture for an exact-singleton retained basename, but every retained
data basename has multiple candidate paths under ADR-0022.

Sr Dev - Claude Build is authorized only to correct that fixture in
`tests/acquisition/test_binance_usdm_harmonic_qualification.py`. The correction must use a
genuinely basename-unique recoverable entry, bind against the complete fixture domain,
prove the lookup precondition, and preserve the migration no-write assertions. Production
is frozen at SHA-256
`2f88ad6e7cfc531fefe3d9c7a9ddbc830741687e93c51450fc826062dffb2c74`.
Claude runs no commands or Git operation and stops with source/test hashes and the test
count. Hermes remains unauthorized. Gate 2 remains unaccepted; next ticket remains
`NONE`.

## Migration fixture correction accepted for reintegration

Review 206 accepts the corrected 315-test source at SHA-256
`e4bd0203668a4488fe56ba4efede53696d908a0a68a227d005e3420badc29dea` and preserves the
committed production source at SHA-256
`2f88ad6e7cfc531fefe3d9c7a9ddbc830741687e93c51450fc826062dffb2c74`.
The failing legacy test now uses a genuinely basename-unique monthly funding-rate entry,
binds against the complete fixture domain, proves its recovery premise, and preserves the
original migration no-write assertions.

Jr Dev - Hermes is authorized only for review 206's corrected one-file reintegration,
qualification-module tests, exact-path Ruff, repository control, restricted whitespace
check, record-207 publication, and the corresponding four-path commit and push. The
sequence stops on its first pytest or Ruff failure and always returns to the reviewer. No
qualification, authority or historical-store mutation, sizing, acquisition, later work,
or next ticket is authorized. Gate 2 remains unaccepted; next ticket remains `NONE`.

## Record-207 migration fixture reintegration published

Hermes integrated review 206's accepted corrected qualification test fixture. The
qualification-module test command passed in 7 seconds:

`.venv/bin/python -m pytest tests/acquisition/test_binance_usdm_harmonic_qualification.py -q --tb=short`

Exact-path Ruff also passed:

`.venv/bin/python -m ruff check src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py tests/acquisition/test_binance_usdm_harmonic_qualification.py`

Hermes published record 207, ran repo-control and restricted whitespace validation, and
stopped for reviewer inspection. No qualification, authority or historical-store mutation,
sizing retry, acquisition, normalization, catalog publication, NautilusTrader, Harmonic
Trader, payoff, PAPER, LIVE, paid source, reduced scope, full-suite, or next-ticket work
was run. Gate 2 remains unaccepted. Next ticket remains `NONE`.

## ADR-0022 integration accepted; isolated authority transition required

Review 208 accepts record 207 and the integrated ADR-0022 qualification source/tests.
The focused 315-test suite, exact-path Ruff, repository control, and restricted whitespace
validation all passed. The historical lock and ledger still end with the prior source
receipt, so ordinary qualification and sizing remain unauthorized.

Sr Dev - Claude Build is authorized only to create the isolated transition module, thin
no-network script, and test module enumerated in review 208. The transition pins the exact
accepted real pre-state, preserves the report/checkpoint/lock/ledger at content addresses,
preserves the existing two receipts, and appends exactly one receipt for qualification
source `2f88ad6e...` and code/config `86ff0eb0...`. The accepted qualification source,
315-test path, existing CLI, sizing paths, repository records, and data may not change.
Claude runs no commands or Git operation and stops with the three hashes and new test
count. Hermes and all transition/data execution remain unauthorized. Gate 2 remains
unaccepted; next ticket remains `NONE`.

## Isolated transition source requires authority-proof correction

Review 209 rejects the first isolated transition drop. The completed-state proof checks
the receipt prefix but not the entire live ledger against the preserved ledger, so a
changed non-receipt binding field such as `download_authorized` can be mirrored into the
lock and pass preflight. Separately, unconditional lock/ledger binding equality makes the
required ledger-first interruption state unreachable. The declared uncompressed manifest
identity is also never stream-proved.

Sr Dev - Claude Build is authorized only to correct the new transition production and
test paths. It must reconstruct and compare the complete expected advanced ledger, make
the exact ledger-first middle state reachable while rejecting every other mismatch,
reject binding/receipt/legacy/envelope/integrity changes, stream-prove the pinned
uncompressed manifest hash and bytes, and add the adversarial coverage in review 209. The
standalone script is frozen at SHA-256
`ada238d22560ddcaf834dff03d0da44c546856090e6133cf5afeb7be3d50aabd`.
All accepted isolation and transaction behavior remains frozen. Claude runs no commands
or Git operation and stops with three hashes and the test count. Hermes and all execution
remain unauthorized. Gate 2 remains unaccepted; next ticket remains `NONE`.

## Isolated transition resume requires correction

Review 210 accepts and freezes review 209's whole-ledger comparison, branch-specific
binding proof, and streamed uncompressed-manifest proof, but rejects the corrected drop.
The transaction unconditionally tries to preserve the live lock and ledger as prior bytes
after preflight, so a ledger-first resume and completed idempotent call both fail once
those authority files have legitimately advanced. The interruption test helper also
removes every synthetic fixture pin when it calls `monkeypatch.undo()`.

Sr Dev - Claude Build is authorized only to correct the new transition production and
test paths. Fresh state alone may publish prior evidence from live pinned bytes. Resumed
and completed states must require, rehash, and reuse all four already-preserved evidence
objects without republishing missing evidence or treating advanced authority bytes as the
prior artifacts. Claude must scope the interruption patch without undoing fixture pins and
add the evidence/resume/idempotence coverage required by review 210. The standalone
script remains frozen at SHA-256
`ada238d22560ddcaf834dff03d0da44c546856090e6133cf5afeb7be3d50aabd`.
Claude runs no command or Git operation and stops with three hashes and the test count.
Hermes and all execution remain unauthorized. Gate 2 remains unaccepted; next ticket
remains `NONE`.

## Advanced transition preflight requires all evidence

Review 211 accepts and freezes the corrected state-aware evidence resolver, recoverable
ledger-first execution, completed no-op, scoped interruption patch, and every prior
authority correction. One narrow gap remains: direct advanced-state `preflight()` can
return authority when prior report or checkpoint evidence is absent or damaged because
the all-evidence resolver is called only later by `apply_path_bound_transition()`.

Sr Dev - Claude Build is authorized only to make advanced preflight call the existing
no-live-authority evidence verifier before returning and extend the existing evidence
matrix to prove direct preflight and apply both reject all four damaged evidence objects.
Fresh preflight and the immediate pre-write recheck remain unchanged. The standalone
script remains frozen at SHA-256
`ada238d22560ddcaf834dff03d0da44c546856090e6133cf5afeb7be3d50aabd`.
Claude runs no command or Git operation and stops with three hashes and the test count.
Hermes and all execution remain unauthorized. Gate 2 remains unaccepted; next ticket
remains `NONE`.

## Focused transition test failure

Review 212 statically accepts and freezes transition production
`f9a1bc89c63b22c974d020044ea8732939358efae00b42f2141bfd0eee34e5e5`
and the standalone script. Under the owner's explicit focused-test authorization, the
reviewer ran the 69-case synthetic suite: 53 failed and 16 passed because the literal-pin
test reloads the module and invalidates the file-level `TransitionError` class alias. The
representative rejection test passes alone. Exact-path Ruff found only the test module's
unused `os` import.

Implementation Dev - Codex Spark is authorized only for the two mechanical test edits
stated at the top of this handoff and in review 212. Production, CLI, all other tests,
records, controls, and data are frozen. Spark runs no command or Git operation and returns
the corrected test hash and unchanged function count. The reviewer will rerun pytest and
Ruff. Hermes and transition/data execution remain unauthorized. Gate 2 remains
unaccepted; next ticket remains `NONE`.

## Transition source and tests accepted for integration

Review 213 accepts transition production `f9a1bc89...`, standalone CLI `ada238d...`, and
test source `60b018f0...`. Under the owner's focused-validation authorization, the reviewer
corrected the test harness and all 69 cases passed; exact-path Ruff and restricted
whitespace validation also passed. The production state machine, complete authority
proof, evidence ordering, recovery, idempotence, receipt, and CLI boundaries are accepted.

Jr Dev - Hermes is authorized only to integrate the three exact accepted paths and
publish record 214 plus the two control updates. It verifies hashes and Git identity,
runs repository control and the exact six-path whitespace check, commits and pushes only
those six paths, and stops for reviewer inspection. It does not rerun pytest or Ruff and
does not execute the transition or any data workflow. Gate 2 remains unaccepted; next
ticket remains `NONE`.

## Record-214 transition integration published

Hermes integrated review 213's three accepted isolated-transition paths at the accepted
hashes. Per review 213, Hermes did not rerun pytest or Ruff and did not execute the
transition or any data workflow.

Hermes published record 214, ran repository control and the exact six-path whitespace
check, and stopped for reviewer inspection. No historical-store transition, ordinary
qualification, sizing source change or retry, acquisition, normalization, catalog
publication, NautilusTrader, Harmonic Trader, payoff, PAPER, LIVE, paid source, reduced
scope, or next-ticket work was run. Gate 2 remains unaccepted. Next ticket remains
`NONE`.

## Transition integration accepted; isolated execution authorized

Review 215 accepts record 214 and confirms `HEAD == origin/main` at `6ab3cf0...`. A fresh
read-only preproof found all ten historical artifacts byte-identical to review 208 and all
four new prior-evidence destinations absent.

Jr Dev - Hermes is authorized only to run review 215's exact transition command. After a
successful `executed=true` result, it runs the identical command once more to prove
`executed=false` idempotence, publishes record 216, updates the two control files, commits
and pushes only those three repository paths, and stops for reviewer inspection. Any
failure stops the sequence. No qualification, sizing, acquisition, tests, lint, network,
or other data work is authorized. Gate 2 remains unaccepted; next ticket remains `NONE`.

## Record-216 path-bound transition execution published

Hermes ran review 215's exact isolated transition command. The first invocation exited
status 0 with `executed=true`, final lock SHA-256
`6cbd044adf4ace577ff8899b2825723e8c0ae99d1fe3c855f2783ce54d7b722e`, amendment-ledger
SHA-256 `2d41fbf009d9803ca5bda05c3a11d75dafe505a1397756e5fafefeb2d1cb90bf`, target
code/config digest `86ff0eb0ee5fa379855745aedb41bb8442b0a244a8c5a740665acc735fba28fb`,
three source receipts, zero samples acquired, zero network requests, and zero credentials
read.

Hermes then ran the identical command once more. It exited status 0 with `executed=false`,
the same final lock and amendment-ledger identities, three source receipts, and zero sample
work. A full 41,369-file store manifest comparison before and after the second command was
identical. Hermes published record 216, ran repository control and the three-path
whitespace check, and stopped for reviewer inspection. Gate 2 remains unaccepted. Next
ticket remains `NONE`.

## Record-218 path-bound qualification execution published

Hermes proved review 217's exact path-bound pre-state at `HEAD == origin/main`
`320d795b346eb30316591f6a6f57bdcb4bb609cf`, confirmed no qualification process was
running, obtained network-enabled execution permission, and ran exactly one ordinary
qualification invocation. The command exited status 0 after 596 seconds and wrote a
changed terminal report 62.

The new report is 13,745,360 bytes at SHA-256
`f27b2ba7e6eff3a8b1385d985c49ee64ef60a394737b1246130d0f37b9015f09`. It reports
`gate_status=QUALIFIED`, `accepted=true`, zero source blockers, zero blocked products,
and seven release-blocked products. The new manifest detail gzip is 11,292,635 bytes at
SHA-256 `64d0f74b8e4696c98d0f96423185fd961aba6c63348d12425e3ec364b888f113`, with
uncompressed SHA-256 `d6c1fac650aaf16d88750da2a40d837f543d0c5fc88c73d463753a576d5bdd17`
and 466,714,158 uncompressed bytes.

The ADR-0022 retained decomposition matched expectation: 73 valid retained requirement
keys, 73 retained verified credit objects, 5,225,416 retained verified credit bytes, 56
selected-manifest consumable objects, and 17 retained complete-cost keys. The report
rejected 176 ambiguous basename-only retained rows for consumability, reuse credit, and
source evidence while preserving lineage.

The live lock and amendment ledger stayed at SHA-256 `6cbd044a...` and `2d41fbf0...`
with the same three-receipt binding. All four transition-preserved evidence objects
remained byte-identical. The store file count changed from 41,369 to 41,372, with
network-cache/snapshot and progress/metadata mutations recorded in record 218. Hermes ran
no retry, second qualification, sizing, bulk acquisition, normalization, catalog
publication, NautilusTrader, Harmonic Trader, payoff, PAPER, LIVE, paid source, reduced
scope, pytest, Ruff, or next-ticket work. Gate 2 remains unaccepted. Next ticket remains
`NONE`.

## Record-223 sizing integration and failed execution published

Hermes verified `HEAD == origin/main` at
`656512b38bcf17b0cbe0343b675f99729cd2c7a4`, integrated the exact accepted sizing
production/test bytes from review 222, and confirmed the frozen sizing CLI hash. Only the
accepted sizing production and test paths differed among the three sizing paths.

Hermes proved the review-222 authority pre-state, confirmed receipt 180 and the sizing
envelope tree were absent, confirmed no sizing or qualification process was running, and
ran the first exact local sizing invocation without loading `.env` or requesting network.
The command exited status 1 after 155 seconds with:

```text
ERROR: a Coinalyze provenance record carries a credential field
```

Per review 222, the nonzero status ended authorization. Hermes did not retry, run the
second idempotence invocation, repair, substitute an artifact, run pytest, run Ruff,
acquire data, normalize, publish a catalog, or perform any Harmonic Trader / payoff /
PAPER / LIVE / next-ticket work.

No sizing receipt or envelope file was produced. The complete `data/cex002_qualify` store
manifest remained identical before and after the failed invocation: 41,372 files and
manifest SHA-256 `f2522d5a3f3152880d42e4e85ead2e5ae64c6d635293ad2ef35c3437025d4ead`.
Gate 2 remains unaccepted. Next ticket remains `NONE`.

## Record-223 acceptance and focused provenance correction

The reviewer accepted Hermes's record-223 integration and stop. Commit
`005f4ee6154725ae7de0acc57e11a8acf702670b` contains exactly the authorized five paths,
is published at `origin/main`, and left the 41,372-file evidence store unchanged. Receipt
180 and the sizing-envelope tree remain absent.

The sizing failure is a source conformance defect. The accepted report safely records
`header_names: ["api_key"]` without a header value, proves header-only authentication, and
contains no credential query parameter. The sizing source incorrectly rejects the mere
presence of that header name because it searches a serialized record for the substring
`api_key`; its synthetic success fixture omitted the real header-name field.

Review 224 authorizes Sr Dev - Claude Build to correct only the sizing production and test
paths. The correction must validate the exact real provenance schema, permit only the
safe `api_key` header name, reject query credentials/header values/unknown fields without
echoing values, preserve every other sizing authority check, and stop for reviewer source
inspection. No integration, tests, sizing execution, data mutation, or later work is
authorized. Gate 2 remains unaccepted and next ticket remains `NONE`.

## Corrected provenance source accepted and integrated execution authorized

The reviewer accepted Claude's review-224 two-file correction at production SHA-256
`bcaca1b1907a89df5020cdbd33c44f49471ff67d0c97d1a303c8225c2cabb592` and test SHA-256
`0a9a3cf0978b596130323e36e495e4fa4d0bc018f21a6d44341e8b9e3bab8177`.
The sizing CLI remains unchanged at SHA-256
`78ee687c734fc94070952d290752acdbd007970fb26c616e5e6845f1de3702ad`.

The correction validates the exact real Coinalyze provenance shape, permits only the safe
header name without a value, rejects query credentials/header values/unknown fields, and
keeps secret values out of failure surfaces and sizing outputs. The corrected test file
has 71 test functions and an expected 153 focused cases.

Review 225 authorizes Hermes to integrate those exact bytes, run the focused suite and
exact-path Ruff, and only on two successes run the corrected local sizing command followed
by one identical idempotence invocation. Hermes then publishes record 226 and only the
authorized paths. No source repair, network, Gate-2 acceptance, acquisition, or later work
is authorized. Gate 2 remains unaccepted and next ticket remains `NONE`.

## Record-226 corrected sizing validation pass and execution failure published

Hermes verified `HEAD == origin/main` at `a9b319898a0b162ff28dd0b5bbb55961fd9b9ac2`,
integrated the exact accepted review-225 sizing production/test bytes, and confirmed the
unchanged sizing CLI. The focused sizing suite passed with 153 cases, and exact-path Ruff
passed over the sizing production, sizing tests, and frozen CLI.

Hermes then ran the first exact corrected local sizing invocation without loading `.env`
or requesting network. It exited status 1 after 160 seconds with:

```text
ERROR: the retained liquidation response covers an unsupported symbol
```

Per review 225, the nonzero status ended authorization. Hermes did not retry, run the
second idempotence invocation, repair, substitute an artifact, acquire data, normalize,
publish a catalog, or perform Harmonic Trader / payoff / PAPER / LIVE / next-ticket work.

No valid receipt 180 was produced. The sizing command created 96 ignored envelope files
totaling 1,890,921 bytes before failing; those data-evidence files were not staged. The
store file count changed from 41,372 to 41,468 and the post-failure manifest SHA-256 is
`361095f2be95d9efab91046b910f76cc514e8e2fc1a79e1d359ead2f13ddedb6`. Gate 2 remains
unaccepted. Next ticket remains `NONE`.

## Record-226 accepted and identity namespace correction authorized

The reviewer accepted Hermes's record-226 integration, 153-case focused pass, Ruff pass,
and required stop after the first sizing invocation exited 1. Commit
`913bf4c10733fe31ed957b9a927b01db48700345` is published with exact scope. Receipt 180
remains absent. The 96 content-addressed Binance sizing envelopes are valid ignored
evidence and remain in place for verified reuse.

The failure is an identity-namespace defect: the report's 569 supported symbols and all
lifecycle keys are Binance-native, while the retained response correctly uses Coinalyze
provider identities. The pinned future-market inventory and report anchor identity already
provide the explicit provider/native mapping. The source compared the two namespaces
directly because its fixture incorrectly used provider identities everywhere.

Review 227 authorizes Claude to correct only sizing production/tests: prove the one-to-one
inventory map, map retained provider symbols before native support/lifecycle checks, prove
the anchor bindings, publish both identities explicitly, and make the fixture/tests model
the real namespaces. Suffix stripping, count-only matching, integration, tests, sizing,
network, data mutation, and later work are not authorized. Gate 2 remains unaccepted and
next ticket remains `NONE`.

## Identity source accepted and corrected sizing retry authorized

The reviewer accepted Claude's provider/native correction at production SHA-256
`aafdf65733e2865f92d89d75ce4a4ba934ce240d3d816e37a9fbe0072749ca82` and test SHA-256
`343d422ce86d217d39459b49d40308125065b6a7873459c7d27ca37a6eda12c8`.
The sizing CLI remains unchanged at SHA-256
`78ee687c734fc94070952d290752acdbd007970fb26c616e5e6845f1de3702ad`.
The corrected test file has 85 functions and an expected 181 focused cases.

The source now proves the 759-row one-to-one inventory identity map, uses native identity
for the 569 supported mappings and lifecycles, translates retained provider symbols through
the pinned mapping, proves the two anchors, rejects collisions, and publishes both identity
namespaces. Reviewer read-only inspection also proved the exact 569+202 partition of all
771 accepted membership identities; the other 190 inventory identities do not enter it.

Review 228 authorizes Hermes to integrate exact bytes, reproduce those real-authority
facts, run focused pytest and Ruff, then only on success run corrected sizing and one
identical idempotence invocation. The 96 existing envelopes must be verified and reused.
No source repair, network, Gate-2 acceptance, acquisition, or later work is authorized.
Gate 2 remains unaccepted and next ticket remains `NONE`.

## Record-229 identity-corrected sizing measurement published

Hermes verified `HEAD == origin/main` at `84824e4f23c3cc444c988f7c4d637dbd02eb3c78`,
integrated the exact accepted review-228 sizing production/test bytes, reproduced the
real-authority identity facts, verified the 96 existing envelopes totaling 1,890,921
bytes, and confirmed receipt 180 was absent.

Focused pytest passed with 181 cases, and exact-path Ruff passed. Hermes then ran the
corrected local sizing command without `.env` or network. The first invocation exited 0,
published receipt 180, reused 96 existing envelopes, and published 2 missing Coinalyze
envelopes. The required identical second invocation exited 0, published no new envelopes,
reused all 98 envelopes, and reproduced identical receipt bytes and evidence-store
manifest.

Receipt 180 is 141,595 bytes at SHA-256
`f2e1fef8156e3af1abd40554e5a8393ee6566e1719cf990a2a49867e5aef185c`. It reports
`storage_preflight_state=blocked` with blocker `available_capacity_insufficient`. Total
future storage is 432,141,608,507 bytes, or 432.141608507 decimal GB / 402.463235433
binary GiB, against post-publication available capacity of 158,559,266,533 bytes.

The receipt preserves the ADR-0023 retained decomposition: 56 manifest-consumable rows, 68
selected retained keys, 5 cost retained keys, 73 valid requirement keys, 73 retained credit
objects, and 5,225,416 retained credit bytes. Coinalyze sizing records 759 inventory
mappings, 569 supported native mappings, 202 typed gaps, retained provider/native anchors
`BTCUSDT_PERP.A -> BTCUSDT` and `ETHUSDT_PERP.A -> ETHUSDT`, 570 projected acquisition
receipts, 29,072,901 projected new raw bytes, and 12,621,439 projected normalized bytes.

Hermes did not accept Gate 2, acquire data, normalize, publish a catalog, run Harmonic
Trader, or perform later work. Gate 2 remains unaccepted. Next ticket remains `NONE`.

## Record-229 accepted and storage architecture corrected

The reviewer accepted commit `2f60d5913f361c82b6960faa582d71845366b5e6` and receipt
180 as the complete reproducible version-1 sizing execution. The complete raw footprint is
20,387,504,203 bytes, of which 20,380,788,328 bytes is projected new allocation after
retained credit. The 432,141,608,507-byte v1 capacity bound is blocked against
158,559,266,533 available bytes because its generic string envelope projects
188,932,621,323 normalized/catalog bytes and its whole-tree publication assumption adds
191,116,312,315 temporary bytes. The exact shortfall is 273,582,341,974 bytes.

ADR-0024 rejects storage purchase, scope reduction, price-only data, or a smaller cost
sample. It preserves every selected raw object, required economic row/field, typed gap,
and lineage fact while sizing the actual typed product schemas and replacing the complete
second release copy with content-addressed partition-atomic publication. Gate 2 remains
blocked until a reviewed v2 receipt proves capacity.

Review 230 authorizes Claude Opus 5 for one exact three-path sizing source/test/CLI drop.
Claude must preserve all accepted authority and v1 evidence, implement the fixed new v2
receipt/envelope namespace and auditable projection math, run no command or Git, and stop
once for reviewer inspection. Next ticket remains `NONE`.

## First ADR-0024 source drop rejected with one correction

The reviewer inspected Claude's exact three-path drop once at production SHA-256
`d33d2cce90fa0b4f8b16736916a00f5bac1a8b0f1a3d18b37cea49f564e10003`, test SHA-256
`91adc68309a728436d9c57bee09bd8a3aae10e4b13932a0007893174a97c24ec`, and CLI SHA-256
`36740c926c32e4973bb31dcb570d3c69b89f9f343d52eb8aed3d33d359d7b23c`.
The test file has 101 functions. No reviewer command execution occurred.

The v2 namespaces, payload/overhead separation, per-partition arithmetic, removal of the
full duplicate normalized allocation, and accepted authority logic are preserved. Review
232 rejects integration because float64 silently rounds financial values; Coinalyze is
still a repeated JSON-string envelope; archive packaging is mislabeled as products while
required trade-flow/funding/basis/membership/gap/liquidation/bundle contracts are absent;
real `retrieval_time` and availability semantics are replaced by fabricated metadata;
partition-local lineage is charged as one global manifest; and daily five-minute metrics
has no calendar row ceiling.

Review 232 authorizes Claude for one consolidated correction in the same three paths.
Claude runs no command or Git and stops once for reviewer inspection. Gate 2 remains
blocked, acquisition unauthorized, and next ticket `NONE`.

## ADR-0024 correction rejected and fee boundary reopened

The reviewer inspected Claude's consolidated three-path correction once at production
SHA-256 `a1772979f6ceb979424c865deeb00ad796377170942f1f15292cb4c4a4806866`,
test SHA-256 `402429f7d12f76b0f818ace989a780a4b5fdfd6885027dc544a5e1a7e4a38e3e`,
and unchanged CLI SHA-256
`36740c926c32e4973bb31dcb570d3c69b89f9f343d52eb8aed3d33d359d7b23c`.
The test file has 109 functions. No source, test, Ruff, sizing, qualification, or
acceptance command was executed.

Review 233 rejects integration. The source rejects the accepted report's intentional
106-logical/96-physical sample aliases; exact-decimal conversion depends on a 28-digit
ambient context despite its 38-digit contract; partition manifests still amortize one
global footer and omit Coinalyze lineage; contribution schemas omit final derived and fee
fields; gap sizing discards 8,317 accepted product-scoped gap records and counts only 202;
funding is incorrectly capped at eight-hour cadence; and new Coinalyze test arithmetic
contradicts the implementation.

ADR-0025 preserves all accepted archive and Coinalyze evidence but reopens the
release-level Gate-1 boundary because the required effective-fee source was never
qualified and the FEE-001 table has zero rows. No developer is authorized. The reviewer
must first qualify a free effective-dated fee authority or publish an explicit
infeasibility/contract decision, then issue one complete correction contract. Gate 2 and
bulk acquisition remain blocked. Next ticket remains `NONE`.
