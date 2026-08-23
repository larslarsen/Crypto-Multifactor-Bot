# CEX-002 V3 Sizing Integration and Execution

**Date:** 2026-08-23
**Actor:** Jr Dev - Hermes
**Reviewer authorization:** `research/sprint_004/265_CEX002_V3_SOURCE_ACCEPTANCE_AND_EXECUTION.md`
**Decision status:** focused validation failed; stopped for reviewer inspection
**Gate 2:** not accepted
**Next ticket:** `NONE`

## Scope

Hermes followed review 265 through exact-byte preproof, staged only the two accepted
modified sizing paths, and ran the authorized focused pytest validation once. The focused
pytest command exited nonzero. Per review 265, Hermes stopped before Ruff and before any
real v3 sizing invocation. Hermes did not request network access, load `.env`, acquire
data, normalize a release, publish a catalog, perform NautilusTrader or Harmonic Trader
work, or start later work.

## Preproof

`HEAD == origin/main` before execution:

```text
6794b41e5691ed591f91a68af2ee425534cd122e
6794b41e5691ed591f91a68af2ee425534cd122e
```

Accepted sizing identities:

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py` | `d4afaa6285733c10311560b9fd68b223ab31fa90b1293a71871ea262daa82f5b` |
| `tests/acquisition/test_binance_usdm_harmonic_sizing.py` | `51029244dc068e85a3ec14381088ac05633047de8f7e8020e98bdafe673e197e` |
| `scripts/research/size_binance_usdm_harmonic_release.py` | `36740c926c32e4973bb31dcb570d3c69b89f9f343d52eb8aed3d33d359d7b23c` |

The sizing test source contained 161 `def test_` functions.

No sizing or qualification process was running:

```text
ps -eo pid=,args= | rg '[b]inance_usdm_harmonic_sizing|[s]ize_binance_usdm_harmonic_release|[p]ytest.*harmonic_sizing|[q]ualify_binance_usdm_harmonic'
exit status: 1
stdout: empty
```

Receipt 258 was absent:

```text
test -e research/sprint_004/258_CEX002_GATE2_STORAGE_SIZING_V3.json
exit status: 1
```

The v3 evidence directory had no Parquet files:

```text
find data/cex002_qualify/evidence/sizing/v3 -type f -name '*.parquet' -print
exit status: 1
stderr: find: 'data/cex002_qualify/evidence/sizing/v3': No such file or directory
```

The accepted manifest detail existed:

```text
data/cex002_qualify/evidence/manifests/sha256/d6c1fac650aaf16d88750da2a40d837f543d0c5fc88c73d463753a576d5bdd17.jsonl.gz
test -f exit status: 0
```

Hermes did not delete or rewrite any v1/v2 receipt or envelope.

## Focused Pytest

Hermes ran the exact focused validation command from review 265:

```bash
PYTHONDONTWRITEBYTECODE=1 timeout --signal=TERM --kill-after=60s 50m \
  .venv/bin/python -m pytest \
  tests/acquisition/test_binance_usdm_harmonic_sizing.py -q --tb=short \
  -k 'not test_the_real_accepted_authority_completes_the_receipt_path'
```

Result:

```text
exit status: 1
tool-reported wall time: 15.0946 seconds
publication_utc_after_failure=2026-08-23T21:45:03Z
```

Pytest reported 30 failing tests:

```text
test_the_receipt_publishes_the_adr0023_credit_decomposition
test_resolved_evidence_and_receipt_carry_no_request_metadata
test_the_receipt_carries_both_identity_namespaces
test_liquidation_projection_uses_its_own_parquet_envelopes
test_end_to_end_receipt_is_complete_and_durably_identical
test_no_cost_row_field_or_sample_is_reduced
test_zero_official_fee_rows_stay_distinct_from_the_fee_gaps
test_the_coinalyze_projection_applies_each_coefficient_once
test_version_one_evidence_is_never_read_or_rewritten
test_v2_envelopes_are_content_addressed_and_reused_not_rewritten
test_the_blocked_and_sufficient_boundary_is_exact[ample]
test_the_blocked_and_sufficient_boundary_is_exact[starved]
test_one_owner_per_validity_byte_across_current_and_future_fields
test_the_v3_capacity_terms_reconcile_exactly
test_prior_version_evidence_is_immutable_and_never_a_v3_target
test_the_stable_receipt_projection_is_the_only_reuse_boundary
test_rerun_returns_the_identical_receipt_under_changed_observations
test_rerun_below_the_reserve_floor_also_returns_the_identical_receipt
test_a_tampered_prior_receipt_is_never_reused[cohort]
test_a_tampered_prior_receipt_is_never_reused[measurements]
test_a_tampered_prior_receipt_is_never_reused[filesystem]
test_a_tampered_prior_receipt_is_never_reused[blockers]
test_a_tampered_prior_receipt_is_never_reused[storage_preflight_state]
test_a_tampered_prior_receipt_is_never_reused[authorization]
test_a_tampered_prior_receipt_is_never_reused[capacity]
test_a_foreign_receipt_at_the_fixed_target_is_never_overwritten
test_capacity_shortfall_blocks_without_false_acceptance
test_sizing_touches_only_its_own_evidence
test_receipt_accounts_for_its_own_exact_length
test_coinalyze_equation_uses_exact_retained_response_identity
```

The dominant receipt-path failure was:

```text
cryptofactors.acquisition.binance_usdm_harmonic_sizing.SizingError:
a projected identity partition names an unclassified native identity |
context={'native_symbol': 'GAP0USDT'}
```

Additional direct assertion failures included:

```text
test_liquidation_projection_uses_its_own_parquet_envelopes:
assert 86304 == 114936

test_the_coinalyze_projection_applies_each_coefficient_once:
assert 46716 == (364 * 207)

test_one_owner_per_validity_byte_across_current_and_future_fields:
assert 1 == (8 + 1)
```

## Commands Not Run

Because focused pytest exited 1, review 265 prohibited further execution. Hermes did not
run:

- exact-path Ruff;
- the first real v3 sizing invocation;
- the second idempotence invocation.

## Receipt and Data Evidence

No valid `research/sprint_004/258_CEX002_GATE2_STORAGE_SIZING_V3.json` receipt was
produced. The real v3 sizing CLI was not run, so there are no v3 receipt facts, capacity
equations, post-publication storage facts, v3 evidence manifest, or idempotence facts to
report. Gate 2 remains not accepted.

## Publication

Hermes stages only the two accepted modified sizing paths, this record, and the two
control-plane files. Receipt 258 is omitted because it was not produced. V3 envelopes,
unrelated dirty files, database sidecars, v1/v2 receipts, and v1/v2 envelopes remain
untouched and unstaged.
