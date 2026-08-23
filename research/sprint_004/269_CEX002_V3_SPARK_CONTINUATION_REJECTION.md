# CEX-002 V3 Spark Continuation Rejection

- **Date:** 2026-08-23
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** review-268 continuation rejected; Spark deauthorized
- **Authorized actor:** Sr Dev - Claude Build
- **Gate 2:** not accepted
- **Next ticket:** `NONE`

## Static inspection

The reviewer inspected the completed continuation once at test SHA-256
`aab6520df28a6a029478eec16ced15ae40012011031535ef6845344f731cb1b9`, unchanged
production SHA-256 `d4afaa6285733c10311560b9fd68b223ab31fa90b1293a71871ea262daa82f5b`,
and unchanged CLI SHA-256
`36740c926c32e4973bb31dcb570d3c69b89f9f343d52eb8aed3d33d359d7b23c`.
The test file has 161 functions and passes static whitespace validation. The reviewer ran
no pytest, Ruff, control, sizing, qualification, network, or data command.

The deterministic accepted matrix identities, membership proof placement, and width-1
validity assertion are accepted as the correction base. The drop remains rejected:

1. `test_liquidation_projection_uses_its_own_parquet_envelopes` is still byte-identical
   to the failing pre-review-267 block and retains the obsolete `ceil_div` projection.
2. `test_the_coinalyze_projection_applies_each_coefficient_once` adds the new ledger but
   deletes the required raw point/framing equation, partition-manifest mapping count, and
   largest-partition assertion. It still omits the required rejected whole-envelope model.
3. An unrelated capacity test was changed from the real serialized key
   `normalized_ratio_numerator_parquet_bytes` to nonexistent key `envelope_numerator`.
   That introduces a deterministic `KeyError` and does not satisfy the requested second
   Coinalyze test assertion.
4. The accepted-membership rows were reordered without need.

Spark has missed the same bounded first-test and rejected-model requirements in two
successive drops. Under the repository's accepted-result quality and reliability routing
rule, Spark is deauthorized and the exact residual moves to one senior corrective
test-source pass. This is not an architecture change.

## Exact senior correction

Edit only `tests/acquisition/test_binance_usdm_harmonic_sizing.py`:

1. Preserve the deterministic `supported_natives` source-gap/typed-gap symbols, the
   membership assertion in the existing full-matrix test, and
   `missing_run_start_ms == 1`. Restore the original accepted-membership row order so
   `BTCUSDC` remains before `GAPUSDT`.
2. Actually edit `test_liquidation_projection_uses_its_own_parquet_envelopes`. Delete its
   obsolete `footer`, `framing`, and `ceil_div` total. Assert
   `allocation["anchor_bytes"] + allocation["additional_dictionary_bytes"] +
   allocation["incremental_bytes"] == allocation["total_payload_bytes"] ==
   projection.projected_typed_payload_bytes`. Assert
   `projection.projected_normalized_bytes == projection.projected_typed_payload_bytes +
   projection.projected_typed_overhead_bytes + projection.projected_manifest_bytes`.
   Preserve provider/native, envelope identity, partition count, largest partition, and
   redaction assertions.
3. In `test_the_coinalyze_projection_applies_each_coefficient_once`, preserve its new
   disjoint ledger equation. Restore the raw equation
   `gross_liquidation_bytes == projected_points * point_charge_bytes +
   liquidation_receipts * framing_charge_bytes`, normalized payload/overhead/manifest
   reconciliation, `partition_manifest_mappings == partition_count`, and
   `largest_partition_bytes > 0`. Add
   `projected_typed_payload_bytes != projected_points * envelope_numerator` in this test.
4. Revert the unrelated `test_the_v3_capacity_terms_reconcile_exactly` line exactly to
   `receipt["coinalyze"]["normalized_ratio_numerator_parquet_bytes"]`.

Preserve exactly 161 test functions and every other byte. Keep production and CLI
byte-identical at the hashes above. Do not run commands, use Git, edit records, integrate,
commit, or push. Stop once and report test hash, both frozen hashes, and test count.

## Boundaries

Receipt 258, Hermes, validation, sizing, acquisition, normalization, catalog,
NautilusTrader, Harmonic Trader, PAPER/LIVE, and later work remain unauthorized pending
one reviewer static inspection. Gate 2 remains not accepted and next ticket remains
`NONE`.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly this record, `docs/handoff/CURRENT_TASK.md`,
and `tickets/CEX-002.md`. Developer source/test/CLI paths and unrelated dirty work are
excluded.
