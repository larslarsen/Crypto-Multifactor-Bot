# CEX-002 Claude Typed Source Test Correction

- **Date:** 2026-08-23
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** second incomplete Spark test drop rejected; one test-only senior correction
- **Authorized actor:** Sr Dev - Claude Build
- **Integration actor after source acceptance:** NONE
- **Gate 2:** not accepted
- **Next ticket:** `NONE`

## Reviewed drop

The reviewer inspected Spark's review-253 test-only drop once at:

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py` | `39eff6a986e114b1c07f5af976709179a8ec5c5ad5d113b6dc4ae743df60d468` (accepted, unchanged) |
| `tests/acquisition/test_binance_usdm_harmonic_sizing.py` | `34520ce233728dd9b8ac8f48b45a56709287f88b3b8a065efc99f33efb6cf836` |
| `scripts/research/size_binance_usdm_harmonic_release.py` | `36740c926c32e4973bb31dcb570d3c69b89f9f343d52eb8aed3d33d359d7b23c` (unchanged) |

The test file contains 144 `def test_` functions. No reviewer pytest, Ruff, sizing,
qualification, control, acceptance, network, or data command was run.

## Accepted progress

The original invalid kline-decimal/redaction test is restored. Spark also added separate
test surfaces for book-depth timestamp success/failure, nullable ratios, invalid nonempty
ratios, and missing required metrics. Preserve those useful boundaries while correcting
their incomplete assertions and fixtures. The production source remains fully accepted
and frozen at the hash above.

## Residual blocker

The purported nullable metrics payload contains nine CSV fields against the accepted
eight-field schema, so it fails at schema width before proving null conversion. It also
uses one all-null row repeatedly rather than the required mixed present/null rows and
does not prove nullable Arrow decimal types or exact present values.

The other new tests still omit required contract checks: timestamp non-nullability and
complete row retention, structural field coordinates and redaction for invalid/empty
timestamps, structural column and redaction for invalid nonempty nullable ratios, and the
exact required-value failure for the two OI level/value fields.

Two Spark passes have not produced an executable complete test contract. Under the
repository's reliability-based routing rule, Claude is now the minimum-usage capable actor
for this final corrective test-source drop. Spark is deauthorized.

## Exact Claude correction and stop

Claude may edit only `tests/acquisition/test_binance_usdm_harmonic_sizing.py`. Preserve
the accepted sizing source and unchanged CLI byte-for-byte. Work from the current test
drop in place; repair or consolidate only the review-252/253 test additions and preserve
the restored invalid kline-decimal/redaction proof.

### 1. Book-depth boundary

Use a retained-style book-depth payload with two UTC-text timestamp rows. Require the
measurement source-row count, measured-row count, and Parquet row count all equal two.
Require the written `timestamp` field to be non-nullable Arrow `int64` and its two values
to equal the exact expected epoch milliseconds.

For invalid and empty timestamp cases, require the correct strict error message, exact
`contribution == binance_usdm_cost_calibration:daily_book_depth`, exact
`column == timestamp`, and absence of the rejected nonempty token from the error string.

### 2. Mixed nullable-metrics boundary

Use one valid eight-field headerless metrics payload with four rows:

1. all four ratios present;
2. both top-trader ratios empty while count-long/short and taker ratios are present;
3. only the taker ratio empty; and
4. all four ratios empty.

Require source-row count, measured-row count, and Parquet row count all equal four. For
each of the four ratios, require a nullable Arrow `decimal128(38,18)` field and the exact
four-value sequence of `Decimal` or `None` implied above. No null position may become
zero, and no row may disappear.

For a nonempty invalid token in a nullable ratio, require the strict decimal error,
exact metrics contribution, exact ratio column, and rejected-token redaction. Separately
parameterize `sum_open_interest` and `sum_open_interest_value` empty tokens and require the
missing-value error, exact contribution, and exact required column.

### 3. Preserve scope

Do not change production, CLI, financial semantics, converters, product schemas, unrelated
fixtures, or unrelated tests. Preserve all review-249 sizing, idempotence, lineage,
capacity, tamper, collision, publication, and v1 protections. Do not delete, skip, xfail,
or weaken a test.

Do not run commands, tests, Ruff, sizing, qualification, control, Git, network,
acquisition, normalization, or data/evidence work. Do not edit repository records. Stop
once after the complete test-only correction and report SHA-256 for the test file, the
unchanged accepted source, and unchanged CLI, plus the final `def test_` function count.

Grok, Sol, Spark, Hermes, integration, execution, acquisition, and later work remain
unauthorized pending reviewer static acceptance. Gate 2 remains not accepted and next
ticket remains `NONE`.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly:

- `research/sprint_004/254_CEX002_CLAUDE_TYPED_SOURCE_TEST_CORRECTION.md`;
- `docs/handoff/CURRENT_TASK.md`; and
- `tickets/CEX-002.md`.

Developer source/test/CLI paths and unrelated dirty work are excluded.
