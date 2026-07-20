# REVIEW-0023 - BIN-001: CHANGES_REQUIRED

**Ticket:** BIN-001 - Binance archive kline normalizer
**Integration reported at:** `727ca56`
**Status:** CHANGES_REQUIRED - RESOLVED (superseded by REVIEW-0025_BIN-001_ACCEPTED.md)
**Next required actor:** Sr Dev - Grok Build
**Date:** 2026-07-19

The strengthened Jr regression exposed a real production-source defect. The v3
normalizer's default returned plan cannot be published by MAN-001, so BIN-001 cannot be
accepted even though the test suite is reported green.

## Production blocker

`normalize_binance_kline` accepts `config_sha256=None` and constructs
`ConfigIdentity(config_sha256="")`. MAN-001 requires a lowercase 64-hex SHA-256, so
`DatasetPublisher.publish` rejects the generated manifest. The API also defaults
`code_commit` to `"unknown"`, which is schema-valid but is not an immutable code identity
for a reproducible dataset.

The new publication test does not demonstrate publication. It wraps
`DatasetPublisher.publish` in `pytest.raises(Exception)` and then asserts the invalid
defaults, converting the known production failure into a passing test.

## Remaining Jr evidence defects

1. The current focused file contains 27 `test_*` functions, while the report and gate
   result claim 25. The recorded validation cannot be accepted as the result of the
   current file.
2. `_month_row` sets `close_time = open_time + 1`. The monthly tests therefore create an
   interval mismatch and merely assert that the rejected row was preserved. They do not
   verify a real calendar-month inclusive close. The `2020-01-31` test name also claims
   February 28 even though 2020 is a leap year.
3. Market tests now cover all three variants and partition units, but still do not assert
   that physical values from CSV fields 5/7/9/10 land in the correct output columns.
4. Valid coverage is checked only as non-null and ordered, not against exact expected
   UTC instants.
5. The reported full integration hash differs from the prior recorded hash only in its
   short prefix while retaining the same remaining suffix. Jr must replace this with
   actual immutable Git output rather than a constructed or pending value.

## Authorized source task - Sr Dev - Grok Build

Edit only `src/cryptofactors/ingest/binance.py`. Make every returned default
`PublishPlan` MAN-001-valid and reproducible: either derive a deterministic canonical
64-hex configuration hash from all identity-bearing normalization configuration when no
hash is supplied, or require and validate an explicit hash. Do not emit an empty hash.
Do not silently publish with `code_commit="unknown"`; require a non-empty immutable code
identity from the caller rather than invoking Git or inferring repository state inside
the normalizer. Preserve all accepted v3 behavior. Do not edit tests, records,
migrations, Git, commits, or pushes. Stop after the source drop.

## Authorized follow-up - Jr Dev - Hermes

After the Sr source drop, integrate without independent production edits. Replace the
broad exception publication test with a successful `DatasetPublisher.publish` assertion
covering both outputs and catalog registration. Pass explicit valid code/config identity
where the Sr API requires it. Correct monthly fixtures to use true calendar boundaries
and inclusive close times, assert no interval error, assert exact coverage instants and
all market-specific physical values, then run the ticket-exact gates. Record the actual
collected count and real commit hash, commit and push, and stop for review.

## Disposition

BIN-001 remains `IN_PROGRESS`. Next ticket authorized: `NONE`.
