# CEX-002 V2 Sizing Integration and Execution

**Date:** 2026-08-23
**Actor:** Jr Dev - Hermes
**Reviewer authorization:** `research/sprint_004/239_CEX002_V2_SIZING_SOURCE_ACCEPTANCE_AND_EXECUTION.md`
**Decision status:** focused validation failed; stopped for reviewer inspection
**Gate 2:** not accepted
**Next ticket:** `NONE`

## Scope

Hermes followed review 239 through exact-byte preproof and the authorized focused pytest
validation. The focused pytest command exited nonzero. Per review 239, Hermes stopped
immediately and did not run Ruff, did not run the real v2 sizing CLI, did not run the
idempotence invocation, did not request network access, did not load `.env`, did not
acquire data, and did not publish a sizing receipt.

## Preproof

`HEAD == origin/main` before execution:

```text
e403a60bda69be4bfd66cda199f0d67b888ca53a
e403a60bda69be4bfd66cda199f0d67b888ca53a
```

Accepted sizing identities:

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py` | `be877786ad308338f51be6986d4b6557a64c0eb8868321d022e1b0c63f0d7241` |
| `tests/acquisition/test_binance_usdm_harmonic_sizing.py` | `b62775ceedd7972e68c83178eb5887ff3f727315a64addce5463e9815a394a93` |
| `scripts/research/size_binance_usdm_harmonic_release.py` | `36740c926c32e4973bb31dcb570d3c69b89f9f343d52eb8aed3d33d359d7b23c` |

The sizing test source contained 137 `def test_` functions.

No sizing or qualification process was running:

```text
ps -eo pid=,args= | rg '[b]inance_usdm_harmonic_sizing|[s]ize_binance_usdm_harmonic_release|[p]ytest.*harmonic_sizing|[q]ualify_binance_usdm_harmonic'
exit status: 1
stdout: empty
```

Receipt 231 was absent:

```text
test -e research/sprint_004/231_CEX002_GATE2_STORAGE_SIZING_V2.json
exit status: 1
```

The v2 evidence directory had no Parquet files:

```text
find data/cex002_qualify/evidence/sizing/v2 -type f -name '*.parquet' -print
exit status: 1
stderr: find: 'data/cex002_qualify/evidence/sizing/v2': No such file or directory
```

The accepted manifest detail existed:

```text
data/cex002_qualify/evidence/manifests/sha256/d6c1fac650aaf16d88750da2a40d837f543d0c5fc88c73d463753a576d5bdd17.jsonl.gz
test -f exit status: 0
```

Hermes did not delete or rewrite any v1 receipt or v1 envelope.

## Focused Pytest

Hermes ran the exact focused validation command from review 239:

```bash
PYTHONDONTWRITEBYTECODE=1 timeout --signal=TERM --kill-after=60s 50m \
  .venv/bin/python -m pytest \
  tests/acquisition/test_binance_usdm_harmonic_sizing.py -q --tb=short \
  -k 'not test_the_real_accepted_authority_completes_the_receipt_path'
```

Result:

```text
exit status: 1
```

The command failed with 34 failing tests. The first repeated authority failure was:

```text
cryptofactors.acquisition.binance_usdm_harmonic_sizing.SizingError:
accepted sizing authority does not match its pinned identity |
context={'authority': 'retained_gate2_credit',
'key': 'data/futures/um/daily/bookDepth/BTCUSDT/BTCUSDT-bookDepth-2020-01-01.zip',
'field': 'credited_checkpoint.byte_size', 'actual': 145, 'expected': 2072}
```

Additional failures included required-product contract membership, partition manifest
mapping counts, exact conversion error text, target-only schema allocation, fee-gap
counts, damaged lineage binding checks, v1 immutability/idempotence receipt paths, receipt
tamper protections, capacity boundary checks, own-evidence scope, receipt self-length
accounting, and Coinalyze retained response identity.

Failed test names reported by pytest:

```text
test_the_receipt_publishes_the_adr0023_credit_decomposition
test_the_required_product_contract_is_complete_and_named_by_the_ticket
test_partition_manifest_mappings_are_counted_per_product_partition
test_resolved_evidence_and_receipt_carry_no_request_metadata
test_the_receipt_carries_both_identity_namespaces
test_end_to_end_receipt_is_complete_and_durably_identical
test_a_failed_conversion_blocks_the_whole_envelope
test_no_cost_row_field_or_sample_is_reduced
test_final_product_schemas_are_complete_and_target_only_fields_are_allocated_once
test_zero_official_fee_rows_stay_distinct_from_the_fee_gaps
test_the_coverage_authority_starts_from_the_full_accepted_matrix
test_damaged_lineage_bindings_block[duplicate_record-repeats a sample record key]
test_damaged_lineage_bindings_block[substituted_digest-report_sample.sha256]
test_damaged_lineage_bindings_block[substituted_size-report_sample.byte_size]
test_damaged_lineage_bindings_block[substituted_family-report_sample.family]
test_damaged_lineage_bindings_block[missing_semantics-no availability semantics]
test_version_one_evidence_is_never_read_or_rewritten
test_v2_envelopes_are_content_addressed_and_reused_not_rewritten
test_the_blocked_and_sufficient_boundary_is_exact[ample]
test_the_blocked_and_sufficient_boundary_is_exact[starved]
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

## Commands Not Run

Because focused pytest exited 1, review 239 prohibited further execution. Hermes did not
run:

- exact-path Ruff;
- the first real v2 sizing invocation;
- the second idempotence invocation.

## Receipt and Data Evidence

No valid `research/sprint_004/231_CEX002_GATE2_STORAGE_SIZING_V2.json` receipt was
produced. No v2 sizing Parquet evidence existed before the run, and no sizing command was
authorized after the validation failure.

## Publication

Hermes stages only the three accepted sizing paths, this record, and the two control-plane
files. Unrelated dirty files, database sidecars, data evidence, v1 receipts, and v1
envelopes remain untouched and unstaged.
