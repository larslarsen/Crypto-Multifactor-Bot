# CEX-002 Gate 1 Stable-Authority Execution Record

Date: 2026-08-20

Actor: Jr Dev — Hermes

## Outcome

**FOCUSED INTEGRATION SUITE FAILED — NO SOURCE COMMIT, NO NETWORK RUN, NO REAL GATE 1 RUN.**

Per review 80, a focused-command failure requires Hermes to record the exact failure in
this record, publish that evidence, and stop without a network run. The accepted nine-path
source/test/fixture drop remains uncommitted and is not integrated. No real qualification
was executed.

## Reviewed identities (verified before execution)

Committed control-plane base:
`HEAD == origin/main == ad7914225cb98c03ba407902258c9861d28d8536`.

All nine reviewed-path SHA-256 values matched review 80 exactly before the run:

| Path | Expected (review 80) | Observed |
|---|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `7e60ed28d56a32b1722d9c6016ff059c188dfed71481aa5865ca367767d14150` | match |
| `scripts/research/qualify_binance_usdm_harmonic_sources.py` | `578f45e2be6f4428cc73560daacb31a305f72501f26f4ea2cd2c718a444fc64b` | match |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `f30c341234286975434fa481c665a1cbb60438ea9a891889bef0ebbab7e0f7e6` | match |
| `tests/acquisition/fixtures/binance_usdm_harmonic_qualification/exchange_info.json` | `9388b67710c51ce0a4219c2e23d57c804d01f4a54b08b340dff1e9bdbb414ed0` | match |
| `tests/acquisition/fixtures/binance_usdm_harmonic_qualification/coinalyze_future_markets.json` | `47416908780ef674efdf1cb3a62cb215c4f48834ad932f9c20e080eb6649b83f` | match |
| `tests/acquisition/fixtures/binance_usdm_harmonic_qualification/coinalyze_liquidation_history_anchors.json` | `d4e7834b6705e8c21329c04fa9738c29030e1da9c674b7d57e9ba4f3977e9ad0` | match |
| `tests/acquisition/fixtures/binance_usdm_harmonic_qualification/coinalyze_open_interest_history_anchors.json` | `30be3ac8ba27213a381675f24a6f83b6de85d139032662101d14e9f8d626f9df` | match |
| `tests/acquisition/fixtures/binance_usdm_harmonic_qualification/coinalyze_funding_rate_history_anchors.json` | `2537212f7b423a991a4ed9aa2413df72843dc059768e53f23260eddfe5de1f3f` | match |
| `tests/acquisition/fixtures/binance_usdm_harmonic_qualification/coinalyze_ohlcv_history_anchors.json` | `8fd1ddd5eb4b498badc4b203831872b3c1b006fb892f196f6d5273932d0de6d5` | match |

## Command sequence (review 80 order)

### 1. Focused CEX-002 suite — FAILED (exit 1)

Command:

```
.venv/bin/python -m pytest tests/acquisition/test_binance_usdm_harmonic_qualification.py -q --tb=short
```

Result: 5 failed, exit 1. Exact failures:

1. `tests/acquisition/test_binance_usdm_harmonic_qualification.py::test_absent_family_prefix_blocks_official_complete`
   at line 583:
   ```
   assert [item["status"] for item in gaps] == ["absent_family_prefix"]
   E   AssertionError: assert ['current_unarchived'] == ['absent_family_prefix']
   ```
   The typed gap emitted for an absent family prefix is `current_unarchived`, not the
   expected `absent_family_prefix`.

2. `tests/acquisition/test_binance_usdm_harmonic_qualification.py::test_cost_calibration_requires_book_depth_and_ticker`
   at line 838:
   ```
   assert cost_both.source_qualification_state == SOURCE_STATE_OFFICIAL
   E   AssertionError: assert 'qualified_with_typed_gaps' == 'official_qualified'
   ```
   The cost-calibration product reports `qualified_with_typed_gaps` where the test
   requires `official_qualified`.

3. `tests/acquisition/test_binance_usdm_harmonic_qualification.py::test_oversized_object_emits_typed_sample_budget_block`
   at line 1291:
   ```
   assert trade.authority != "inaccessible"
   E   AssertionError: assert 'inaccessible' != 'inaccessible'
   E    +  where 'inaccessible' = ProductMatrixRow(product='binance_usdm_trade', authority='inaccessible', official_complete=False, source_gate=True, release_blocked=True, typed_gap_symbols=(), coverage_gap_kinds=('absent_family_prefix', 'interior_month_gap')).authority
   ```
   The sampled `binance_usdm_trade` row is classified `authority='inaccessible'` with
   `coverage_gap_kinds=('absent_family_prefix', 'interior_month_gap')`; the test requires
   a sampled, non-inaccessible authority.

4. `tests/acquisition/test_binance_usdm_harmonic_qualification.py::test_retained_object_is_reported_once`
   at line 1563:
   ```
   assert plan["unique_retained_objects"] == 1
   E   assert 0 == 1
   ```
   The resumed sample plan reports zero unique retained objects where the test requires
   exactly one retained object to be reported once.

5. `tests/acquisition/test_binance_usdm_harmonic_qualification.py::test_exchange_info_row_missing_identity_fields_fails_closed`
   at line 2601:
   ```
   with pytest.raises(SourceQualificationError, match="missing required contract identity"):
   E   AssertionError: Regex pattern did not match.
   E     Expected regex: 'missing required contract identity'
   E     Actual message: "exchangeInfo payload has no authenticated serverTime | context={'server_time': 'None'}"
   ```
   The fail-closed error raised is `exchangeInfo payload has no authenticated serverTime`
   instead of the expected `missing required contract identity` regex.

### Commands 2–5 (NOT RUN)

Per review 80, the sequence stops at the first focused-command failure. The
atomic-download suite, Ruff, `check_repo_control.py`, and `git diff --check` were not
executed. No source, test, or fixture path was staged, committed, or pushed. No network
qualification was performed.

## Integrity assertions

- No source/test/fixture path was modified, staged, committed, or pushed.
- `data/cex002_qualify` was not touched; its retained raw objects, listings, checkpoints,
  and reports are unchanged.
- No secret value appears in this record. The `.env` key was not loaded or printed.
- `git diff --check` was not run (command 5); the pre-failure staged path list was empty
  and the nine reviewed paths were left untouched in the working tree.

## Consequence

The accepted review-80 source drop does not satisfy its own focused test contract at the
integration gate. Jr integration, the source commit, and both real Gate 1 runs remain
unauthorized. The reviewer must disposition the five test-contract failures before any
further execution.