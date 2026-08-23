# CEX-002 V3 Spark Test Residual

- **Date:** 2026-08-23
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** review-267 Spark drop rejected on bounded test residual
- **Authorized actor:** Implementation Dev - Codex Spark continuation
- **Gate 2:** not accepted
- **Next ticket:** `NONE`

## Static inspection

The reviewer inspected the completed test-only drop once at test SHA-256
`e3fc3eab270743992edd1b91308d733543284aac33edc7f8813fb8b8542089c8`, unchanged
production SHA-256 `d4afaa6285733c10311560b9fd68b223ab31fa90b1293a71871ea262daa82f5b`,
and unchanged CLI SHA-256
`36740c926c32e4973bb31dcb570d3c69b89f9f343d52eb8aed3d33d359d7b23c`.
The test file still has 161 functions and passes static whitespace validation. No reviewer
pytest, Ruff, control, sizing, qualification, network, or data command was run.

The matrix symbols, second Coinalyze ledger equation, and null validity expectation move
in the accepted direction, but the drop is not accepted:

1. It changes `unmapped` from accepted membership identity `GAPUSDT` to extra inventory
   identity `DOGEUSDT` and removes `GAPUSDT` from `accepted_membership`. That changes the
   fixture's universe and breaks the rule that a Coinalyze non-mapping is an accepted
   universe identity. Neither change was authorized.
2. It places the membership assertion inside fixture construction instead of the existing
   full-matrix coverage test required by review 267.
3. `test_liquidation_projection_uses_its_own_parquet_envelopes` remains unchanged and
   still asserts the superseded envelope-ratio projection that failed record 266.
4. The second Coinalyze test proves the new sum but omits the required rejection of
   multiplying a complete measured envelope by every projected point.
5. The `classifications` dictionary's `symbol` line has an indentation defect.

## Exact continuation

Edit only `tests/acquisition/test_binance_usdm_harmonic_sizing.py`:

1. Restore `unmapped = ["GAPUSDT"]`, restore the `("GAPUSDT", "USDT", "USDT",
   "GAP")` accepted-membership row, and restore normal indentation of the `symbol` key.
   Preserve the new deterministic `supported_natives` matrix symbols.
2. Remove the membership assertion from fixture setup. Add the equivalent assertion to
   `test_the_coverage_authority_starts_from_the_full_accepted_matrix`, deriving the set
   from `accepted["accepted_membership"]` and checking every source-gap and typed-gap
   symbol in `accepted["matrix_rows"]`.
3. In `test_liquidation_projection_uses_its_own_parquet_envelopes`, replace the obsolete
   `ceil_div` envelope-ratio total with the exact allocation equation:
   `anchor_bytes + additional_dictionary_bytes + incremental_bytes ==
   total_payload_bytes == projected_typed_payload_bytes`. Also require normalized bytes
   to equal typed payload plus typed overhead plus partition-manifest bytes. Preserve its
   provider/native, envelope identity, partition count, largest partition, and redaction
   assertions.
4. In `test_the_coinalyze_projection_applies_each_coefficient_once`, preserve the accepted
   ledger, raw point/framing equation, normalized reconciliation, and mapping count. Add
   the explicit rejected-model assertion that typed payload is not
   `projection.projected_points * projection.envelope_numerator`. Remove now-unused local
   variables.

Preserve the width-1 validity correction and exactly 161 test functions. Keep production
and CLI byte-identical at the hashes above. Do not edit any other path; do not run commands,
use Git, integrate, commit, or push. Stop once and report the test hash, both frozen hashes,
and test count.

## Boundaries

Receipt 258, Hermes, validation, sizing, acquisition, normalization, catalog,
NautilusTrader, Harmonic Trader, PAPER/LIVE, and later work remain unauthorized pending
reviewer static acceptance. Gate 2 remains not accepted and next ticket remains `NONE`.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly this record, `docs/handoff/CURRENT_TASK.md`,
and `tickets/CEX-002.md`. Developer source/test/CLI paths and unrelated dirty work are
excluded.
