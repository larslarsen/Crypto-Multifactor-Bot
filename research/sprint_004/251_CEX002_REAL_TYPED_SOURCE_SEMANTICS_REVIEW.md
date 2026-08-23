# CEX-002 Real Typed Source Semantics Review

- **Date:** 2026-08-23
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** record-250 real-authority failure consolidated into one senior correction
- **Authorized actor:** Sr Dev - Claude Build
- **Integration actor after source acceptance:** NONE
- **Gate 2:** not accepted
- **Next ticket:** `NONE`

## Reviewed evidence

The reviewer inspected Hermes's complete record 250 once. Hermes proved the review-249
identities, then focused pytest and exact-path Ruff both passed. The first real v2 sizing
invocation ran for 156 seconds and exited 1 with `a typed integer column is not a strict
integer`. Hermes correctly stopped without an idempotence invocation, receipt 231, v2
envelope publication, or later work.

The integrated identities remain:

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py` | `32153fe509929eedd64731f57046eb0cc838cb3296ea681e195481358af694bc` |
| `tests/acquisition/test_binance_usdm_harmonic_sizing.py` | `6a9fdb3103f9259545864d5341a1d61739df15e9669b2a325fa8a615cae327a3` |
| `scripts/research/size_binance_usdm_harmonic_release.py` | `36740c926c32e4973bb31dcb570d3c69b89f9f343d52eb8aed3d33d359d7b23c` (unchanged) |

The test file contains 139 `def test_` functions. The reviewer ran no pytest, Ruff,
sizing, qualification, control, acceptance, network, or data-mutation command.

## Complete retained-cohort diagnosis

The CLI deliberately redacted the structural exception context, so the reviewer performed
a read-only source/schema audit across all 96 retained physical objects and 56,259 rows.
It found exactly two source-contract mismatches:

1. all 600 retained `daily/bookDepth` rows carry `timestamp` as Binance UTC text such as
   `2025-07-23 07:36:03`, while `_BOOK_DEPTH` incorrectly dispatches that field to the
   strict integer-lexeme converter; and
2. five of nine retained `daily/metrics` objects contain genuine empty source cells in
   four ratio fields: 535 `count_toptrader_long_short_ratio`, 535
   `sum_toptrader_long_short_ratio`, one `count_long_short_ratio`, and 556
   `sum_taker_long_short_vol_ratio` cells. These are 1,627 empty cells across 557 rows.

The reviewer then evaluated the complete retained cohort under the correction contract
below: 491,411 source cells checked, 1,627 explicitly declared nulls, and zero remaining
conversion failures. No source token, row, object, or field is removed by this decision.

## Existing architecture decides the representation

No new ADR is required. ADR-0024 requires target timestamps to be integers, retains every
valid book-depth field and row, and forbids dropping a failed row or replacing missing
data with zero. ADR-0025 already requires UTC text to become epoch units through integer
calendar arithmetic. Therefore:

- the book-depth source token is parsed as `KIND_TIMESTAMP_TEXT` and stored as exact
  integer epoch milliseconds; it is not retained as a normalized string and is not
  passed through `datetime.timestamp()` or binary floating point; and
- the four empirically missing metrics ratios are nullable exact decimals. An empty token
  is a typed null only for an explicitly nullable source column. It is never zero,
  forward-filled, inferred, or grounds for dropping the row.

## One correction contract

Claude may edit only:

1. `src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py`;
2. `tests/acquisition/test_binance_usdm_harmonic_sizing.py`.

Leave `scripts/research/size_binance_usdm_harmonic_release.py` byte-identical.

### A. Correct book-depth timestamp dispatch

Declare `_BOOK_DEPTH.timestamp` with source kind `KIND_TIMESTAMP_TEXT`. Preserve its name,
source field, non-nullability, Arrow `int64` target, exact epoch-millisecond unit, and every
book-depth row and field. Reuse the accepted strict UTC timestamp converter and its
integer-calendar arithmetic. Update synthetic book-depth fixture tokens to the real
Binance lexical form rather than preserving the false integer fixture.

Tests must write a headed or headerless retained-style book-depth row, read the typed
Parquet result, and prove the timestamp is the exact expected epoch-millisecond integer,
the schema is non-nullable `int64`, and every row remains. Invalid or empty timestamps
must still block without exposing the rejected token.

### B. Preserve real missing metrics as typed nulls

Declare exactly these four source-derived fields nullable:

- `count_toptrader_long_short_ratio`;
- `sum_toptrader_long_short_ratio`;
- `count_long_short_ratio`;
- `sum_taker_long_short_vol_ratio`.

Keep `create_time`, `symbol`, `sum_open_interest`, and `sum_open_interest_value` required.
At typed-batch conversion, map a whitespace-empty token to `None` only when that exact
source column is declared nullable. Every nonempty token still passes through the same
strict context-independent converter. Do not introduce a global empty-token exception,
change `convert_decimal`, zero-fill, forward-fill, synthesize, round, or discard a row.

Tests must use a mixed metrics payload containing present values and each observed empty
ratio pattern. Prove every source row is written, the four schema fields are nullable
`decimal128(38,18)`, missing cells read back as null, and present cells remain exact. Also
prove a nonempty invalid lexeme in a nullable ratio still blocks and an empty required OI
level/value still blocks. The existing derived OI level/change and gap-break semantics
must remain unchanged.

### C. Preserve accepted sizing and publication behavior

Preserve every review-249 correction and accepted contract: canonical first-return and
rerun equality, five cost parent/component identities, all eleven final product schemas,
complete row/field accounting, stable prior comparison and internal wholeness, semantic
envelope counts, the six-component capacity equation, exact retained-credit lineage,
causal derivations, and all tamper, collision, no-follow, race, content-addressed
publication, and v1-immutability protections. Do not delete, skip, xfail, or weaken any
test to obtain agreement.

## Exact Claude authorization and stop

Work from the integrated paths in place. Do not reset, restore, checkout, stash, discard,
or replace either file wholesale. Do not run commands, tests, Ruff, sizing, qualification,
control, Git, network, acquisition, normalization, or data/evidence work. Do not edit any
research, ticket, handoff, ADR, receipt, manifest, database, or catalog record.

Stop once after the complete two-path source/test correction. Report SHA-256 for both
edited paths and the unchanged CLI, plus the final `def test_` function count. Sol, Grok,
Spark, Hermes, integration, execution, acquisition, and later work remain unauthorized
pending reviewer static acceptance. Gate 2 remains not accepted and next ticket remains
`NONE`.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly:

- `research/sprint_004/251_CEX002_REAL_TYPED_SOURCE_SEMANTICS_REVIEW.md`;
- `docs/handoff/CURRENT_TASK.md`; and
- `tickets/CEX-002.md`.

Developer source/test/CLI paths and unrelated dirty work are excluded.
