# CEX-002 Typed Source Test Residual Review

- **Date:** 2026-08-23
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** review-252 production accepted; test drop rejected on one bounded residual
- **Authorized actor:** Implementation Dev - Codex Spark
- **Integration actor after source acceptance:** NONE
- **Gate 2:** not accepted
- **Next ticket:** `NONE`

## Reviewed drop

The reviewer inspected Spark's complete review-252 drop once at:

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py` | `39eff6a986e114b1c07f5af976709179a8ec5c5ad5d113b6dc4ae743df60d468` |
| `tests/acquisition/test_binance_usdm_harmonic_sizing.py` | `86d0f3c159293e22ca0a2b9b1b2ea9f2f3cf6452fca36bfadc19f136ad9a01d2` |
| `scripts/research/size_binance_usdm_harmonic_release.py` | `36740c926c32e4973bb31dcb570d3c69b89f9f343d52eb8aed3d33d359d7b23c` (unchanged) |

The test file contains 139 `def test_` functions. No reviewer pytest, Ruff, sizing,
qualification, control, acceptance, network, or data command was run.

## Accepted production correction

Preserve the sizing source byte-for-byte. It implements review 251 literally:

- `_BOOK_DEPTH.timestamp` dispatches through the existing exact UTC-text converter while
  retaining a non-nullable Arrow `int64` target;
- exactly the four named metrics ratio columns are nullable exact decimals;
- empty-to-`None` occurs only after a real source field is resolved and only when that
  exact column is explicitly nullable;
- every nonempty token still uses the strict converter; and
- no row filter, zero fill, forward fill, inference, new parser, or product change exists.

The realistic book-depth fixture token and final-product nullable assertions are also
accepted. All review-249 behavior remains in place.

## One test-source blocker

The modified `test_a_failed_conversion_blocks_the_whole_envelope` removed its existing
nonempty invalid kline-decimal and redaction proof, replacing it with only an empty
required OI-level proof. Review 252 explicitly prohibited weakening an existing test.

The new assertions also stop short of review 252's required boundary proof. They do not
prove:

- book-depth timestamp schema is non-nullable Arrow `int64`;
- invalid and empty book-depth timestamps still block and redact the rejected token;
- a mixed metrics payload retains every present/null row;
- all four ratio fields are nullable `decimal128(38,18)` in the written table;
- non-null ratio values survive exactly;
- each supported empty pattern becomes null rather than zero; or
- a nonempty invalid lexeme in a nullable ratio still blocks and is redacted.

## Exact Spark correction and stop

Spark may edit only `tests/acquisition/test_binance_usdm_harmonic_sizing.py`. Preserve the
accepted sizing source and unchanged CLI byte-for-byte. Do not delete or rewrite the
accepted assertions already added except where needed to remove duplication after the
complete tests exist.

1. Restore the pre-review-252 invalid kline-decimal test behavior: `not-a-number` blocks
   as a non-decimal lexeme, the contribution coordinate is exact, and the token is absent
   from the error string.
2. Add a retained-style book-depth envelope test with UTC-text timestamp rows. Read the
   Parquet table and prove every row remains, the timestamp field is non-nullable Arrow
   `int64`, and exact expected epoch-millisecond values were written. Prove separate
   invalid and empty timestamp tokens block with their structural field coordinate and
   without exposing the token.
3. Add a mixed retained-style metrics envelope test containing present ratios, the
   observed top-trader-pair absence, the observed taker-ratio-only absence, and an
   all-four-ratios absence. Prove source rows, measured rows, and Parquet rows are equal;
   all four fields are nullable `decimal128(38,18)`; present values round-trip exactly;
   missing values are `None`, never zero; and no row is dropped.
4. Prove a nonempty invalid token in one nullable ratio still raises the strict decimal
   error with the exact structural column coordinate and redaction. Separately prove an
   empty required `sum_open_interest` or `sum_open_interest_value` still raises the
   required-value error.

Do not change production source, the CLI, financial semantics, converter behavior,
fixtures outside this boundary, or unrelated tests. Do not run commands, tests, Ruff,
sizing, qualification, control, Git, network, acquisition, normalization, or data/evidence
work. Do not edit repository records.

Stop once after the complete test-only correction and report SHA-256 for the test file,
the unchanged accepted sizing source, and the unchanged CLI, plus the final `def test_`
function count. Claude, Grok, Sol, Hermes, integration, execution, acquisition, and later
work remain unauthorized pending reviewer static acceptance. Gate 2 remains not accepted
and next ticket remains `NONE`.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly:

- `research/sprint_004/253_CEX002_TYPED_SOURCE_TEST_RESIDUAL_REVIEW.md`;
- `docs/handoff/CURRENT_TASK.md`; and
- `tickets/CEX-002.md`.

Developer source/test/CLI paths and unrelated dirty work are excluded.
