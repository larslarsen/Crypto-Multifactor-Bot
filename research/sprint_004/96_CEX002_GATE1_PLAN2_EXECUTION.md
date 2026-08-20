# CEX-002 Gate 1 Plan-2 Execution Record

Date: 2026-08-20

Actor: Jr Dev — Hermes

Ticket: CEX-002, Gate 1 source procurement

## Outcome

**COMMANDS 1–5 PASSED. PLAN VERSION 2 MIGRATION PASSED. BOTH REAL RUNS EXITED 2
(BLOCKED) AND AGREED. SEMANTIC RESUME IDENTITY PASSED. GATE 1 REMAINS BLOCKED ON
STORAGE AND UNRESOLVED MEMBERSHIP.**

Review 95 authorized the one-time plan-2 migration under the accepted round-trip source
and reauthorized the two-run real execution against the preserved store. Both runs
qualified Coinalyze and produced identical semantic identity; the release stays blocked
by `gate2_storage_insufficient` (universe requirement ~8.66 TB vs ~186 GB local) and the
`unresolved_membership` coverage state. Exit 2 is the intended BLOCKED disposition for a
complete, non-accepted qualification run.

## Verified identities

Committed control-plane base: `HEAD == origin/main == bf3ed3eb0b807b5718d88c7927dc7b1389779243`.

Both review-95 accepted hashes matched before execution:

| Path | Expected (review 95) | Observed |
|---|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `733e7589b705d9b584269e3e8df06fdade19d98b6f18e3d5b65760009eeb87d3` | match |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `a8e41aae63d800bdca76f6b1321e3c51fb47211e7c5a2a3692e1089f50021a6d` | match |

Pre-migration lock SHA-256 confirmed as the review-95 value
`45c2207934952997398f1e8a90865094c3e1fea9dec5654db3bfba21e94720bf` (version 1).

## Command sequence (review 95 order) — all PASSED

### 1. Focused CEX-002 suite — PASS, exit 0
`.venv/bin/python -m pytest tests/acquisition/test_binance_usdm_harmonic_qualification.py -q --tb=short`
149 collected, 149 passed (progress dots: 72 / 72 / 5).

### 2. Atomic-download suite — PASS, exit 0
`.venv/bin/python -m pytest tests/test_download_atomicity.py -q --tb=short`
11 collected, 11 passed.

### 3. Ruff — PASS, exit 0
`.venv/bin/python -m ruff check src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py scripts/research/qualify_binance_usdm_harmonic_sources.py tests/acquisition/test_binance_usdm_harmonic_qualification.py`
`All checks passed!`

### 4. Repo control — PASS, exit 0
`python3 scripts/check_repo_control.py` → `Repo control check: PASS`

### 5. Whitespace check — PASS, exit 0
`git show --check --oneline --no-renames HEAD` → no whitespace errors.

## One-Time Plan-2 Migration — PASS

Executed the review-95 migration block verbatim from repository root. Every assertion
passed and the block printed the post-migration identity:

```
CEX-002 plan version 2 authorization: PASS
plan_digest=d6eb52ff73711df669e9388d06a6abca92cb61cc86a17169b7ed62f369f132c1
code_config_digest=0ca6e4f1d0bbdb58e21c1b374a9616ab13593584c8006ceedbf56c3de9220a99
lock_sha256=e04a5ce2f2513cc8a0f4e6698dcbf9d43c5a7bec0295021ca5d431ff886f0d84
```

Post-migration `data/cex002_qualify/cex002_sample_plan_lock.json` (SHA-256
`e04a5ce2f2513cc8a0f4e6698dcbf9d43c5a7bec0295021ca5d431ff886f0d84`):

- kind: sample plan lock; version 1; plan_version 2
- plan_digest: `d6eb52ff73711df669e9388d06a6abca92cb61cc86a17169b7ed62f369f132c1`
  (unchanged across the plan-1 → plan-2 migration, as JSON-serialized plan content is
  identical)
- inputs.code_config_digest: `0ca6e4f1d0bbdb58e21c1b374a9616ab13593584c8006ceedbf56c3de9220a99`
  (the only changed plan input; `differences(old) == ("code_config_digest",)`)
- locked_at: `2026-08-20T21:28:09.298199+00:00`
- history: `[{"plan_version": 0}, {"plan_version": 1}]` (appended row preserves the old
  inputs, plan, and plan digest)
- plan: 146 entries (86 `reuse_retained`, 14 `alias`, 46 `blocked`), 46 blocked
  `sample_budget_exceeded` entries, unique_retained_objects 86, unique_new_objects 0,
  new_download_bytes 0
- retained_snapshot: 118 content-addressed objects, 825,587,609 bytes
- plan blocked required_bytes: 209,163,978
- budget_snapshot: allowance_bytes_at_lock 0; budget_bytes 268,435,456;
  cumulative_spent_max_bytes_at_lock 1,015,198,547; max_object_bytes 67,108,864

The migration used only `SamplePlanLock.lock_plan` / `flush`; no relock flag, plan
reselection, manual JSON edit, deletion, rename, replacement, or reconstruction.

## Bounded real execution (plan version 2)

Invocation (identical for both runs, `.env` loaded into the environment, store and
progress path preserved):

```
/bin/bash -lc 'set -a; . ./.env; set +a; .venv/bin/python scripts/research/qualify_binance_usdm_harmonic_sources.py --store-root data/cex002_qualify --progress-path data/cex002_qualify/cex002_qualification_progress.json --report-path <path>'
```

### First run — EXIT 2 (BLOCKED), 765 s
Report: `/tmp/cex002_gate1_plan2_roundtrip_first.json`, 26,320,909 bytes, SHA-256
`1ecc0be5b40c2cbaceb997e927a88dad99688cc7b4d343eaa92cb4a68762da3b`.

### Second run — EXIT 2 (BLOCKED), 771 s
Report: `research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json`, 26,320,909 bytes,
SHA-256 `dce2a2396c6b250be928f4cde217ce49419561f958301ad97afbd479b6b39e31`.

Raw exit statuses captured from the invocation wrapper: **R1_EXIT=2, R2_EXIT=2** (agree;
exit 1 would have stopped, exit 0 or 2 permits the second run).

### Semantic resume identity — PASS

The authoritative comparison from the review-95 sequence:

```
.venv/bin/python -c 'import json; from pathlib import Path; from cryptofactors.acquisition.binance_usdm_harmonic_qualification import drop_identity_volatility; a=json.loads(Path("/tmp/cex002_gate1_plan2_roundtrip_first.json").read_text()); b=json.loads(Path("research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json").read_text()); assert drop_identity_volatility(a)==drop_identity_volatility(b); print("Gate 1 semantic resume identity: PASS")'
```

Output: `Gate 1 semantic resume identity: PASS`.

The only raw differences between the two reports are execution-plane fields dropped by
the canonical `drop_identity_volatility` (`_IDENTITY_DROP_KEYS`): `generated_at`,
response/membership `retrieved_at`, `observed_at`, `server_time_ms`,
`response_sha256`, `retained_contract_snapshots` (run 1: 3, run 2: 4 — a fourth contract
snapshot was retained on disk by the second run), and the `gate2_feasibility`
`local_available_bytes`/`shortfall_bytes` (disk free space at run time). All
source-authority semantics are byte-identical after the canonical drop.

## Report evidence (run 2 report; run 1 identical after the canonical drop)

- gate: `gate_1_source_procurement`; gate_status: `BLOCKED`; accepted: false; ticket:
  `CEX-002`
- universe_source:
  `official_vision_union_listing_with_evidence_based_perpetual_membership`
- Coinalyze: **qualified = true**; anchors BTCUSDT → `BTCUSDT_PERP.A` and ETHUSDT →
  `ETHUSDT_PERP.A`; matched_anchor_market_count 2; binance_perpetual_market_count 759;
  native_identity_validated_markets 759; key_present true
  (`query_contains_key`); universe_support supported_count **569** of 771 confirmed
  perpetuals, unmapped_count **202**; attribution
  "Coinalyze; cite https://coinalyze.net when redistributed"
- membership class_counts: confirmed_perpetual 771, dated_delivery_candidate 46,
  delivery_non_perpetual 4, settlement_artifact_candidate 17, tradifi_perpetual 170
- discovered_symbols: 1004; current_perpetual_symbols: 698;
  current_contracts_authenticated: true
- resume: physical_families_inventoried 20, progress_objects 278, recovered_samples 0,
  rehash_required true, reused_samples 100, unverified_retained_sample_keys 0
- samples: 100 (all `reused_existing`, 0 new downloads; 0 recoveries)
- retry: attempts 6, base_delay_s 0.5, jitter_ratio 0.25, max_attempts 5,
  max_delay_s 30.0, retries 0, incidents []
- incidents: 92 = 91 `sample_budget_exceeded` + 1 `gate2_storage_insufficient`
- listing_checkpoint: entries 29,413, reused_requests 39,805, fetched_requests 0,
  unclaimed_evidence 0
- budget: exhausted true, breach_state unresolved, budget_bytes 268,435,456,
  cumulative_spent_max_bytes 1,015,198,547, charge_count 0, reservation_count 0,
  planned_total_bytes 0, transferred_total_bytes 0
- storage: physical_source_requirement
  compressed_raw_bytes **8,662,211,210,669**, object_count 5,123,061,
  universe_size 771; gate2_feasibility gate2_storage_state **insufficient**,
  local_available_bytes run1 186,677,514,240 / run2 185,976,057,856,
  shortfall_bytes run1 **8,474,518,497,882** / run2 **8,475,219,954,266**,
  physical_compressed_raw_bytes 8,662,211,210,669,
  projected_new_compressed_raw_bytes 8,661,196,012,122, raw_storage_sufficient false,
  retained_verified_credit_bytes 805,792,081 (86 retained objects),
  normalized_catalog_bytes state unknown (treated as false, never assumed zero)
- physical store size: `du -sb data/cex002_qualify` = 4,443,407,816 bytes

## Product matrix (12 rows)

| Product | Source qualification | Coverage | Authority | Official complete | Discovered | Listed objects | Listed bytes | Samples | Release blocked | Gap kinds |
|---|---|---|---|---|---|---|---|---|---|---|
| binance_usdm_perpetual_membership | membership_unresolved | unresolved_membership | membership_unresolved | false | 771 | 771 | 6,628,196,148,904 | 87 | true | 9 |
| binance_usdm_trade | official_qualified | unresolved_membership | official | false | 990 | 1,297,467 | 6,174,436,174,147 | 27 | true | 8 |
| binance_usdm_bar_1m | official_qualified | unresolved_membership | official | false | 1002 | 709,650 | 61,196,652,414 | 14 | true | 6 |
| binance_usdm_trade_flow | derived_excluded | not_applicable | unsupported | false | 771 | 0 | 0 | 0 | false | 0 |
| binance_usdm_open_interest_5m | official_qualified | unresolved_membership | official | false | 975 | 595,471 | 6,291,378,762 | 7 | true | 9 |
| binance_usdm_funding_realized | official_qualified | unresolved_membership | official | false | 917 | 21,425 | 21,645,197 | 7 | true | 9 |
| binance_usdm_funding_indicative | official_qualified | unresolved_membership | official | false | 936 | 660,936 | 28,705,337,062 | 14 | true | 8 |
| binance_usdm_mark_index_basis | official_qualified | unresolved_membership | official | false | 991 | 2,067,175 | 99,853,687,857 | 42 | true | 9 |
| binance_usdm_liquidation_observed | secondary_qualified | unresolved_membership | secondary | false | 771 | 0 | 0 | 686 | true | 1 (`coinalyze_symbol_unmapped`) |
| binance_usdm_cost_calibration | official_qualified | unresolved_membership | official | false | 945 | 584,222 | 2,448,204,498,577 | 3 | true | 9 |
| binance_usdm_coverage_gap | derived_excluded | not_applicable | unsupported | false | 771 | 0 | 0 | 0 | false | 0 |
| binance_usdm_harmonic_bundle | derived_excluded | not_applicable | unsupported | false | 771 | 0 | 0 | 0 | false | 0 |

Blocked products (9): binance_usdm_perpetual_membership, binance_usdm_trade,
binance_usdm_bar_1m, binance_usdm_open_interest_5m, binance_usdm_funding_realized,
binance_usdm_funding_indicative, binance_usdm_mark_index_basis,
binance_usdm_liquidation_observed, binance_usdm_cost_calibration.

The `liquidation_observed` product moved from `unresolved_membership`/Coinalyze-unknown
to **secondary_qualified** with authority `secondary` (Coinalyze liquidation history
works and qualifies anchors), but remains release_blocked solely on
`coinalyze_symbol_unmapped` (202 of 771 confirmed perpetuals have no Coinalyze mapping).

## Publication

- `docs/handoff/CURRENT_TASK.md` and `tickets/CEX-002.md` next-required-actor set to
  `Lead Quantitative Finance Researcher/Engineer - inspect Gate 1 stable-authority execution`.
- Published records: `research/sprint_004/96_CEX002_GATE1_PLAN2_EXECUTION.md`,
  `research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json` (second-run report,
  SHA-256 `dce2a2396c6b250be928f4cde217ce49419561f958301ad97afbd479b6b39e31`).
- No source, test, fixture, data, or unrelated dirty path is staged. `HEAD == origin/main`
  established; Hermes stops here.

## Integrity assertions

- No secret value appears in this record; the API key was loaded only from `.env` and
  never printed or placed in a command argument.
- The preserved store was not deleted, renamed, replaced, reconstructed, or relocked; the
  plan-2 migration used only the authorized `lock_plan`/`flush` path and preserved the
  plan content digest.
- No source/test/fixture path was modified, staged, committed, or pushed.
- Raw exit statuses 2 and 2 were captured from the invocation wrapper, not inferred.
- The semantic resume identity used the canonical source `drop_identity_volatility`.

## Consequence

Gate 1 remains BLOCKED (exit 2) on two independent blockers with Coinalyze now qualified:

1. **Storage:** the physical source requirement (8,662,211,210,669 bytes for 5,123,061
   objects) exceeds local available capacity (~186 GB) by ~8.47 TB; the budget is
   exhausted/unresolved and Gate 2 storage state is insufficient.
2. **Coverage:** all release-blocked products carry `unresolved_membership` coverage;
   `liquidation_observed` is secondary-qualified but blocked on 202 unmapped Coinalyze
   symbols.

The reviewer must disposition both blockers (storage capacity / plan scope and the
unresolved-membership coverage semantics) before any further real execution. No reduced
universe, omitted derivatives fields, or price-only substitute is authorized.