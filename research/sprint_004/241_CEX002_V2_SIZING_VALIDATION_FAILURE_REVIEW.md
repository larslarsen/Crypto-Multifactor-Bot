# CEX-002 V2 Sizing Validation Failure Review

- **Date:** 2026-08-23
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** review-240 validation failure rejected; one consolidated correction authorized
- **Authorized actor:** Sr Dev - Claude Build
- **Integration actor after source acceptance:** NONE
- **Gate 2:** not accepted
- **Next ticket:** `NONE`

## Reviewed execution

Hermes integrated the exact review-239 identities and ran the authorized focused pytest
command. The integrated identities are:

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py` | `be877786ad308338f51be6986d4b6557a64c0eb8868321d022e1b0c63f0d7241` |
| `tests/acquisition/test_binance_usdm_harmonic_sizing.py` | `b62775ceedd7972e68c83178eb5887ff3f727315a64addce5463e9815a394a93` |
| `scripts/research/size_binance_usdm_harmonic_release.py` | `36740c926c32e4973bb31dcb570d3c69b89f9f343d52eb8aed3d33d359d7b23c` |

The test file has 137 functions. Focused pytest exited 1 with 34 failed tests. Hermes
correctly stopped before Ruff and before either sizing invocation. No receipt 231 or v2
Parquet evidence was produced; no network, acquisition, normalization, catalog, model, or
later work ran. Exact execution evidence is in review record 240.

No reviewer pytest, Ruff, sizing, qualification, control, acceptance, network, or data
command was run. Static inspection groups the 34 failures into one production root cause
that cascades through receipt tests and six stale test patterns. Do not repair 34 tests
individually.

Preserve the complete retained-credit key-set join, all review-237 corrections, and every
previously accepted authority, financial-semantic, conversion, security, publication,
v1-immutability, capacity, and idempotence invariant.

## 1. Keep retained bytes distinct from requirement bytes

The first repeated failure is:

```text
field='credited_checkpoint.byte_size', actual=145, expected=2072
```

Reviewed source `build_retained_archive_bindings` lines 3049-3168 compares a credited
checkpoint object's verified local byte length to `PhysicalObject.byte_size`. Those are
different ADR-0023 facts. The checkpoint value is the real retained content-addressed
object length already rehashed by `prove_retained_acquisition_credit`; the physical object
value is the complete acquisition-requirement listing size. A retained cost witness can
therefore be 145 bytes while the required full object is 2,072 bytes. Equality is false
authority, not a safety check.

Keep both facts exact and separate:

- require the credited checkpoint byte length to be a positive integer and preserve the
  credit proof over the actual retained bytes;
- where an accepted sample binding exists, compare its report/sample byte length to the
  checkpoint retained-object length, not to the requirement listing size;
- continue serializing `requirement_byte_size` from `PhysicalObject.byte_size` in the
  projected manifest;
- do not subtract or relabel requirement bytes as retained bytes, and do not weaken the
  exact 73-key credit, hash, sidecar, retrieval, availability, or full-set joins; and
- add an explicit test where the credited retained-object size intentionally differs from
  its requirement-listing size and both values remain independently correct.

This one production defect occurs before receipt construction and cascades through 24 of
the 34 reported failures.

## 2. Correct all stale test patterns in the same drop

Repair the remaining tests literally without weakening production:

1. In `test_the_required_product_contract_is_complete_and_named_by_the_ticket`, the
   no-taker-flow assertion must inspect the premium-index contribution set it just built,
   not all contributions, which necessarily include the required trade-flow product.
2. In `test_partition_manifest_mappings_are_counted_per_product_partition`, the complete
   one-object-per-family fixture has daily and monthly inputs. Bar and trade flow each
   therefore map two raw objects, and basis maps six, with manifest charges of 14, 14, and
   42 at the test's seven-byte rate. Preserve the one aligned 744-row target grid.
3. In `test_a_failed_conversion_blocks_the_whole_envelope`, match the exact pinned error
   contract `not a decimal lexeme`; do not change the correct converter message back to
   the obsolete `not a number` wording.
4. In the final-schema allocation test, instrument identity fields legitimately recur in
   every product schema and are charged once per product row. Exempt those shared identity
   fields from any cross-product uniqueness assertion while retaining within-schema
   uniqueness and uniqueness of product-specific derived fields.
5. In the synthetic coverage-authority test, fee gaps equal the fixture's complete
   accepted membership count, not stale literal `3`.
6. In `test_damaged_lineage_bindings_block`, an additional identical alias is allowed by
   the binder and rejected by the accepted 106/96/10 decomposition proof. Exercise that
   proof for the duplicate case. For substituted digest/size/family/availability cases,
   choose a fixture key with exactly one report sample record so the intended checkpoint
   mismatch is reached instead of an earlier legitimate-alias disagreement.

Keep the complete 137-test source; replace stale assertions rather than deleting tests or
adding skips. Repair any directly adjacent assertion that is mechanically the same stale
assumption, but make no unrelated refactor.

## Exact Claude authorization and stop

Claude Build may edit only:

1. `src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py`;
2. `tests/acquisition/test_binance_usdm_harmonic_sizing.py`;
3. `scripts/research/size_binance_usdm_harmonic_release.py` only if mechanically required;
   otherwise leave it byte-identical.

Work from integrated `HEAD` in place. Do not reset, restore, checkout, discard, or
wholesale replace files. Claude does not run commands or tests, mutate evidence/data, use
Git, or write research, ticket, handoff, ADR, receipt, envelope, database, manifest, or
catalog records. Stop once with SHA-256 for all three allowed paths, marking unchanged
paths, plus the final `test_` function count.

Sol and Grok are deauthorized. Hermes and all integration/execution are unauthorized until
reviewer static acceptance. Gate 2 remains not accepted, acquisition and all later work
remain unauthorized, and next ticket remains `NONE`.

## Reviewer publication scope

Under the AGENTS.md reviewer exception, the reviewer may stage, commit, and push exactly:

- `research/sprint_004/241_CEX002_V2_SIZING_VALIDATION_FAILURE_REVIEW.md`;
- `docs/handoff/CURRENT_TASK.md`;
- `tickets/CEX-002.md`.

Developer source/test/CLI paths and all unrelated dirty work are excluded.
