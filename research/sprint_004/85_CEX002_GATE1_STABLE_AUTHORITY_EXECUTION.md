# CEX-002 Gate 1 Stable-Authority Execution Record

Date: 2026-08-20

Actor: Jr Dev — Hermes

## Outcome

**FOCUSED LINT COMMAND FAILED — NO SOURCE COMMIT, NO NETWORK RUN, NO REAL GATE 1 RUN.**

Per review 84, a focused-command failure requires Hermes to record the exact failure in
this record, publish that evidence, and stop before network. The accepted nine-path
source/test/fixture drop remains uncommitted and is not integrated. No real qualification
was executed.

## Reviewed identities (verified before execution)

Committed control-plane base:
`HEAD == origin/main == 2402f92c25239376095d74c52ea97ac2e2b8585b`.

All nine reviewed-path SHA-256 values matched review 84 exactly before the run:

| Path | Expected (review 84) | Observed |
|---|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `7e60ed28d56a32b1722d9c6016ff059c188dfed71481aa5865ca367767d14150` | match |
| `scripts/research/qualify_binance_usdm_harmonic_sources.py` | `578f45e2be6f4428cc73560daacb31a305f72501f26f4ea2cd2c718a444fc64b` | match |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `d2e172e90cdda8f2740b4b53fe213a019e374750aeb2db3db49e4b508e4a4ae5` | match |
| `tests/acquisition/fixtures/binance_usdm_harmonic_qualification/exchange_info.json` | `9388b67710c51ce0a4219c2e23d57c804d01f4a54b08b340dff1e9bdbb414ed0` | match |
| `tests/acquisition/fixtures/binance_usdm_harmonic_qualification/coinalyze_future_markets.json` | `47416908780ef674efdf1cb3a62cb215c4f48834ad932f9c20e080eb6649b83f` | match |
| `tests/acquisition/fixtures/binance_usdm_harmonic_qualification/coinalyze_liquidation_history_anchors.json` | `d4e7834b6705e8c21329c04fa9738c29030e1da9c674b7d57e9ba4f3977e9ad0` | match |
| `tests/acquisition/fixtures/binance_usdm_harmonic_qualification/coinalyze_open_interest_history_anchors.json` | `30be3ac8ba27213a381675f24a6f83b6de85d139032662101d14e9f8d626f9df` | match |
| `tests/acquisition/fixtures/binance_usdm_harmonic_qualification/coinalyze_funding_rate_history_anchors.json` | `2537212f7b423a991a4ed9aa2413df72843dc059768e53f23260eddfe5de1f3f` | match |
| `tests/acquisition/fixtures/binance_usdm_harmonic_qualification/coinalyze_ohlcv_history_anchors.json` | `8fd1ddd5eb4b498badc4b203831872b3c1b006fb892f196f6d5273932d0de6d5` | match |

## Command sequence (review 84 order)

### 1. Focused CEX-002 suite — PASS

`.venv/bin/python -m pytest tests/acquisition/test_binance_usdm_harmonic_qualification.py -q --tb=short`

84 collected, 84 passed, exit 0. This includes the corrected oversized-object fixture
(with affirmative current-perpetual membership and `current_contracts` supplied) and the
immutable-plan resume test (one unique new object, zero unique retained objects, zero
retained bytes, positive planned new-download bytes, unchanged single transferred ledger
charge).

### 2. Atomic-download suite — PASS

`.venv/bin/python -m pytest tests/test_download_atomicity.py -q --tb=short`

11 passed, exit 0.

### 3. Ruff — FAILED (exit 1)

Command:

```
.venv/bin/python -m ruff check src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py scripts/research/qualify_binance_usdm_harmonic_sources.py tests/acquisition/test_binance_usdm_harmonic_qualification.py
```

Result: `Found 51 errors` (all `F401` unused-import), exit 1. All 51 findings are in the
accepted test path `tests/acquisition/test_binance_usdm_harmonic_qualification.py`; the
accepted production module and CLI produce no lint findings.

The 51 unused imports, by line in the test file:

- line 12: `dataclasses.replace`
- line 22: `cryptofactors.acquisition.binance_usdm_harmonic_qualification.CONTRACT_METADATA_FILENAME`
- line 23: `...CONTRACT_SNAPSHOT_DIRNAME`
- line 24: `...COINALYZE_ANCHOR_SYMBOLS`
- line 27: `...COVERAGE_UNRESOLVED_MEMBERSHIP`
- line 31: `...LEDGER_NO_TRANSFER`
- line 32: `...LEDGER_TRANSFERRED`
- line 33: `...LEGACY_BUDGET_UNRESOLVED`
- line 34: `...LEGACY_PLAN_BACKUP_FILENAME`
- line 35: `...MEMBERSHIP_CONFIRMED`
- line 36: `...MEMBERSHIP_DATED_DELIVERY`
- line 37: `...MEMBERSHIP_DELIVERY`
- line 39: `...MEMBERSHIP_SETTLEMENT_ARTIFACT`
- line 41: `...MEMBERSHIP_UNRESOLVED`
- line 42: `...MEMBERSHIP_UNSUPPORTED_SEMANTICS`
- line 43: `...OFFICIAL_INCREMENTAL_ENDPOINTS`
- line 44: `...PLAN_INPUTS_CHANGED`
- line 46: `...SAMPLE_PLAN_LOCK_FILENAME`
- line 48: `...SOURCE_STATE_MEMBERSHIP`
- line 49: `...SOURCE_STATE_OFFICIAL`
- line 50: `...SOURCE_STATE_SAMPLE_PENDING`
- line 52: `...SEMANTICS_INCOHERENT_IDENTITY`
- line 53: `...SEMANTICS_SUPPORTED`
- line 54: `...SEMANTICS_UNKNOWN_STATUS`
- line 55: `...SEMANTICS_UNKNOWN_UNDERLYING`
- line 58: `...BudgetLedger`
- line 61: `...ExchangeInfoResponse`
- line 67: `...OfficialContractMetadataStore`
- line 76: `...SamplePlan`
- line 77: `...SamplePlanEntry`
- line 78: `...SamplePlanLock`
- line 82: `...build_family_inventory`
- line 83: `...build_sample_plan`
- line 84: `...canonical_contract_row`
- line 85: `...classify_membership`
- line 86: `...contract_close_ms`
- line 87: `...contract_provenance`
- line 88: `...contract_semantics_state`
- line 89: `...exchange_info_server_time_ms`
- line 90: `...family_product_map`
- line 93: `...is_confirmed_perpetual_row`
- line 97: `...listing_authority_digest`
- line 98: `...listing_authority_manifest`
- line 99: `...membership_evidence_digest`
- line 100: `...object_period`
- line 102: `...plan_content_digest`
- line 109: `...retained_evidence_digest`
- line 110: `...retained_evidence_snapshot`
- line 111: `...validate_exchange_info_response`
- line 112: `...validate_sample_plan`
- line 114: `...verify_retained_object`

The production module and CLI paths in the same Ruff invocation reported no findings.

### Commands 4–5 (NOT RUN)

Per review 84, the sequence stops at the first focused-command failure.
`check_repo_control.py` and `git diff --check` were not executed. No source, test, or
fixture path was staged, committed, or pushed. No network qualification was performed.

## Integrity assertions

- No source/test/fixture path was modified, staged, committed, or pushed.
- `data/cex002_qualify` was not touched; its retained raw objects, listings, checkpoints,
  metadata, and reports are unchanged.
- No secret value appears in this record. The `.env` key was not loaded or printed.
- The pre-failure staged path list was empty and the nine reviewed paths were left
  untouched in the working tree.

## Consequence

The accepted review-84 test source fails the focused lint gate on 51 unused imports. Jr
integration, the source commit, and both real Gate 1 runs remain unauthorized. The
reviewer must disposition the lint failure before any further execution.