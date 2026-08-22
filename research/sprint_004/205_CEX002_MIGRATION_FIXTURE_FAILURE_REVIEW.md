# CEX-002 Migration Fixture Failure Review

**Date:** 2026-08-22
**Reviewer:** Lead Quantitative Finance Researcher/Engineer
**Decision:** `INTEGRATION_RECORD_ACCEPTED_TEST_CORRECTION_REQUIRED`
**Gate 1:** Source finding remains accepted; affected publication authority is suspended
**Gate 2:** Not accepted

## Reviewed integration

Hermes committed and pushed record 204 and exactly the five paths authorized by review
203 at commit `441a47713b359b485ef938d5af4cfb81317a1eb7`. `HEAD` and `origin/main`
match that commit. The integrated identities are:

| Path | SHA-256 | Decision |
|---|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `2f88ad6e7cfc531fefe3d9c7a9ddbc830741687e93c51450fc826062dffb2c74` | Accepted, committed, and frozen |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `0f9086db07fb0a4024135a7f07370d9cf9a98beca8bd20a8a829f322153fb867` | Rejected; one fixture correction required |

Hermes correctly stopped after the first acceptance command failed, skipped Ruff, then
published the required failure record and passed repository control and the restricted
whitespace check. Record 204 is accepted as an accurate integration-stop record. The
reviewer performed read-only static inspection only and ran no test, linter,
repository-control, acceptance, qualification, sizing, network, or data-mutation command.

## Finding

### High - the migrated legacy test contains no recoverable exact-singleton key

`test_migration_does_not_adopt_a_recoverable_missing_checkpoint_entry` binds its retained
checksum index to the checkpoint `objects` mapping and then searches for a complete row
whose basename has an exact full-key binding. The fixture built by
`_accepted_v4_candidate` contains monthly and daily Kline paths with the same basenames.
Consequently every retained data row has multiple candidate paths under ADR-0022 and
`checksums.lookup(name)` correctly returns `None`; the test raises `StopIteration` before
reaching the migration behavior it exists to prove.

This is a fixture defect, not evidence that the frozen production implementation is
wrong. The old test's premise became false when its lookup was mechanically domain-bound.
The correction must construct a genuinely recoverable missing checkpoint entry whose
basename is unique across the complete candidate domain, not bind an artificial
singleton. A monthly funding-rate object is the established fixture pattern. Bind the
precondition to the complete fixture domain, explicitly prove the selected key is in that
domain and its lookup is non-`None`, delete only that row, and preserve the existing
record/flush and byte-identical checkpoint assertions through the reviewed migration.

The correction may add a narrowly scoped test helper or parameterize the accepted-v4
fixture if needed to establish that real premise. It must not weaken the complete-domain
rule, alter production, change the migration contract, or modify unrelated tests.

## Claude test-only authority

Sr Dev - Claude Build using Claude Opus 5 is authorized to edit only:

- `tests/acquisition/test_binance_usdm_harmonic_qualification.py`.

Correct only the failing migration fixture described above. Production must remain
byte-identical at
`2f88ad6e7cfc531fefe3d9c7a9ddbc830741687e93c51450fc826062dffb2c74`.
Preserve all other accepted ADR-0022 behavior and the exact 315-test function count. Any
narrow helper change may alter only fixture construction.

Claude runs no test, linter, control, qualification, sizing, network, data mutation, Git,
commit, or push. Return the unchanged production hash, corrected test hash, and
test-function count, then stop for reviewer inspection.

## Stop boundary

Hermes remains unauthorized until the corrected test source is accepted. No sizing retry,
qualification execution, authority mutation, acquisition, normalization, catalog
publication, NautilusTrader, Harmonic Trader, payoff, PAPER, LIVE, paid-source,
reduced-scope, or next-ticket work is authorized. Gate 2 remains unaccepted and next
ticket remains `NONE`.
