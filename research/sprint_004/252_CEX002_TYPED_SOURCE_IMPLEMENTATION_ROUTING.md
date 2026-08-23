# CEX-002 Typed Source Implementation Routing

- **Date:** 2026-08-23
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** route review-251's fully decided mechanical implementation to Spark
- **Authorized actor:** Implementation Dev - Codex Spark
- **Integration actor after source acceptance:** NONE
- **Gate 2:** not accepted
- **Next ticket:** `NONE`

## Routing correction

Review 251 completed the architectural and source-semantic decision. No developer is being
asked to decide whether a field is a timestamp, whether a missing ratio is zero, which
columns are nullable, or how missingness affects financial meaning. The accepted authority
and ADR-0024/0025 decide every one of those facts exactly.

The remaining implementation is a reviewer-bounded low/medium-risk mechanical adapter and
test-source change within Spark's formal scope. Claude Build is therefore deauthorized
before source work begins. No source identity has changed since review 251.

## Exact Spark task

Spark may edit only:

1. `src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py`;
2. `tests/acquisition/test_binance_usdm_harmonic_sizing.py`.

Leave `scripts/research/size_binance_usdm_harmonic_release.py` byte-identical.

Implement review 251 literally:

1. change only `_BOOK_DEPTH.timestamp` source dispatch from `KIND_INTEGER` to
   `KIND_TIMESTAMP_TEXT`, preserving its non-nullable Arrow `int64` epoch-millisecond
   target and using the existing exact timestamp converter;
2. declare exactly the four named metrics ratio source columns nullable exact decimals;
3. in typed-batch conversion, map a whitespace-empty token to `None` only for an
   explicitly nullable source-derived column, while every nonempty token still uses its
   existing strict converter and every empty non-nullable source token still fails;
4. update the synthetic book-depth token to the retained Binance UTC-text form; and
5. add focused test source proving exact book-depth epoch milliseconds and non-nullable
   `int64`, complete row retention, all four nullable decimal ratio fields and null
   round-trip, exact present values, invalid nonempty nullable-ratio rejection, and empty
   required OI level/value rejection.

Do not add a financial fallback, general null coercion, new timestamp parser, row filter,
zero fill, forward fill, inferred value, product/schema rename, CLI change, or unrelated
refactor. Preserve every review-249 sizing/idempotence/publication protection and every
existing test.

## Exact Spark authorization and stop

Work from the integrated paths in place. Do not reset, restore, checkout, stash, discard,
or replace either file wholesale. Do not run commands, tests, Ruff, sizing, qualification,
control, Git, network, acquisition, normalization, or data/evidence work. Do not edit any
research, ticket, handoff, ADR, receipt, manifest, database, or catalog record.

Stop once after the complete two-path source/test drop. Report SHA-256 for both edited
paths and the unchanged CLI, plus the final `def test_` function count. Claude, Grok, Sol,
Hermes, integration, execution, acquisition, and later work remain unauthorized pending
reviewer static acceptance. Gate 2 remains not accepted and next ticket remains `NONE`.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly:

- `research/sprint_004/252_CEX002_TYPED_SOURCE_IMPLEMENTATION_ROUTING.md`;
- `docs/handoff/CURRENT_TASK.md`; and
- `tickets/CEX-002.md`.

Developer source/test/CLI paths and unrelated dirty work are excluded.
