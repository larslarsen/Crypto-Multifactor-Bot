# CEX-002 V3 Focused Test Failure Review

- **Date:** 2026-08-23
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** record 266 accepted as faithful execution; focused validation rejected
- **Authorized actor:** Implementation Dev - Codex Spark
- **Gate 2:** not accepted; corrected validation pending
- **Next ticket:** `NONE`

## Review outcome

The reviewer accepts record 266 and commit `742a166` as a faithful execution of review
265. Exact-byte preproof succeeded, the accepted sizing source/test/CLI identities and
161-test count matched, and Hermes stopped after the first nonzero command without running
Ruff or either real sizing invocation. No receipt 258, v3 data evidence, acquisition,
normalization, catalog, NautilusTrader, Harmonic Trader, PAPER/LIVE, or later work was
produced.

The 30 failures reduce to one fixture defect and three stale assertion blocks. They do not
reopen ADR-0027 or the accepted production allocation model:

1. The fixture's product matrix invents `GAP0USDT`, `GAP1USDT`, and `TYPED*USDT`
   identities that are absent from its accepted membership classifications. The
   production fail-closed check correctly rejects those unclassified identities. Real
   product-scoped coverage and typed-gap records name accepted universe identities.
2. Two Coinalyze tests still assert the superseded whole-envelope/per-point projection.
   Production now publishes the accepted disjoint row-group anchor, additional dictionary,
   and incremental-row ledger.
3. One validity test expects a null nullable non-dictionary value to own its non-null
   physical width. The accepted current-null rule allocates only its one validity byte;
   the non-null `expected_grid_count` remains eight bytes.

The dominant `GAP0USDT` exception accounts for every receipt-path failure. The three direct
assertion failures are exactly the stale blocks above. One bounded test-source correction
therefore covers the complete observed failure set; no production or architecture change
is authorized.

## Implementation-dev correction

Edit only `tests/acquisition/test_binance_usdm_harmonic_sizing.py`. Keep production source
and CLI byte-identical at:

| Path | Required SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py` | `d4afaa6285733c10311560b9fd68b223ab31fa90b1293a71871ea262daa82f5b` |
| `scripts/research/size_binance_usdm_harmonic_release.py` | `36740c926c32e4973bb31dcb570d3c69b89f9f343d52eb8aed3d33d359d7b23c` |

Make exactly these corrections:

1. In the accepted fixture's `matrix_rows`, replace invented `GAP{index}USDT` and
   `TYPED{index}USDT` identities with deterministic selections from
   `supported_natives`, preserving every product, family, status, count, and product scope.
   A product-scoped identity may recur across products. Do not add classifications for
   nonexistent contracts and do not weaken the production classifier.
2. Extend the existing full-matrix coverage test, without adding a test function, to prove
   that every source-gap and typed-gap symbol is present in `accepted_membership`.
3. Rewrite `test_liquidation_projection_uses_its_own_parquet_envelopes` so typed payload
   equals `allocation.anchor_bytes + allocation.additional_dictionary_bytes +
   allocation.incremental_bytes`; require that sum to equal
   `allocation.total_payload_bytes`. Preserve provider/native, partition-count,
   largest-partition, and redaction checks. Replace the obsolete envelope-ratio total;
   do not change production.
4. Rewrite `test_the_coinalyze_projection_applies_each_coefficient_once` to prove the same
   disjoint allocation equation, retain the rejection of multiplying a complete measured
   envelope by every projected point, retain the independent raw point/framing equation,
   and retain exact payload + overhead + partition-manifest reconciliation and mapping
   count.
5. In `test_one_owner_per_validity_byte_across_current_and_future_fields`, expect
   `missing_run_start_ms` current width `1` for its null fixture value. Keep
   `expected_grid_count == 8` and every reference/current identity ownership assertion.

Preserve all other source and tests and keep exactly 161 `def test_` functions. Do not run
pytest, Ruff, control, sizing, qualification, network, or data commands. Do not edit
repository records, use Git, integrate, commit, or push. Stop once and report the test
SHA-256, both unchanged frozen hashes, and test-function count.

## Boundaries

Receipt 258, Hermes integration, validation, sizing execution, acquisition,
normalization, catalog publication, NautilusTrader, Harmonic Trader, PAPER/LIVE, and later
work remain unauthorized pending one reviewer static inspection. Gate 2 remains not
accepted and next ticket remains `NONE`.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly:

- `research/sprint_004/267_CEX002_V3_FOCUSED_TEST_FAILURE_REVIEW.md`;
- `docs/handoff/CURRENT_TASK.md`; and
- `tickets/CEX-002.md`.

Developer source/test/CLI paths, receipts, evidence, and unrelated dirty work are excluded.
