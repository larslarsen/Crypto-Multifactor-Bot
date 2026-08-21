# CEX-002 Listing Residual Test Review

Date: 2026-08-21

Reviewer: Lead Quantitative Finance Researcher/Engineer

Reviewed base: `6153a15f1278fdf26516e7d445a55d32e3e63157`

Subject review: `research/sprint_004/118_CEX002_LISTING_CORRECTION_SOURCE_REVIEW.md`

Reviewed hashes:

| Path | SHA-256 | Disposition |
|---|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `b6077bf833ae59b2414b441564764179fc0dcff0db6cec3457139a5a26df53e8` | frozen from review 118 |
| `scripts/research/qualify_binance_usdm_harmonic_sources.py` | `45e0f6990df6a71d6197a6b981270ae63b79897553595e6a9b05f912ecfb3f63` | accepted and frozen |
| `src/source_audit/download.py` | `f231930f743f4b2f415dd84a96ec3c1ec3b1c1efab5deb7536db57fce5473fa5` | accepted and frozen |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `daf1d522d227d3afc5fa350c4db1c8ec3f439c81d7b3d8490441a56e0bd9c241` | rejected |
| `tests/test_download_atomicity.py` | `30388dba0568912b7bbe3f83c5454de89cd8cf5cd1288f260d30cfda0bd8d587` | accepted and frozen |

The CEX test source contains 186 uniquely named test functions. The atomic-download test
source contains 18 uniquely named test functions. The reviewer ran no test, Ruff,
repository-control, network, data, candidate, or migration command.

## Decision

**ACCEPT AND FREEZE ALL FOUR IMPLEMENTATION/ATOMIC PATHS. REJECT ONLY THE CEX TEST
SOURCE FOR TWO GUARANTEED FAILURES.**

The CLI now attempts both cleanup actions, preserves an active body failure, and selects
the first cleanup failure after a successful body. The shared pooled transport constructs
one client under concurrent first use, closes successfully exactly once, refuses reopening,
and does not increment `clients_closed` when the underlying close raises. The checkpoint
mapping proof now uses isolated checkpoint-enabled `TransportObjectIndex` instances and
normalizes only real retrieval times and local roots. These directions are accepted.

Hermes integration remains unauthorized until the last test-source defects are corrected.

## Findings

### 1. The accumulated cleanup test asserts the superseded error rule

`test_cli_cleanup_flushes_the_checkpoint_even_when_close_fails` makes the qualification
body raise `SourceQualificationError`, then still expects `module.main` to raise the pool
close error. The corrected CLI deliberately preserves the active body failure: it prints
the qualification error, attempts both cleanup actions, reports the cleanup failure, and
returns 1. The test therefore necessarily fails because no `RuntimeError` propagates.

Update this existing test to assert exit 1, both cleanup attempts, body-error precedence,
and redacted stderr containing both the body and cleanup failure. Keep the separate
successful-body/double-cleanup-failure test proving that the first cleanup failure
propagates. Do not change the accepted CLI.

### 2. The concurrent retry test raises a non-retryable exception type

`test_concurrent_distinct_retry_failures_are_canonically_ordered` raises raw
`httpx.ConnectError` inside `RetryRunner.run`. The accepted retry contract retries the
project's `DownloadError` wrapper; a raw httpx exception is intentionally classified as
non-retryable. Each worker therefore exits on its first call outside the caught
`SourceQualificationError`, no incidents are journaled, and the test later reads a journal
file that was never created.

Use deterministic retryable `DownloadError` failures with distinct redacted labels. Keep
the controlled forward/inverted scheduling, and prove two attempts per request, canonical
report incidents, canonical durable journal incidents, identical final order under both
schedules, and no raw secret/query value. Do not broaden the production retry classifier
to accept raw provider exceptions.

## Claude test-only authorization

Sr Dev - Claude Build using Claude Opus 5 is authorized to edit only:

- `tests/acquisition/test_binance_usdm_harmonic_qualification.py`.

The four accepted hashes above, 17 fixtures, and every other path are frozen. Claude makes
only the two test corrections specified here, removes no test, and changes no production
contract.

Claude performs no test, Ruff, repository-control, network/data run, candidate execution,
migration, integration, repository-record edit, ADR edit, Git operation, commit, push,
catalog work, Nautilus work, Harmonic Trader work, payoff analysis, PAPER, or LIVE work.
It stops for reviewer source inspection with the exact CEX test hash, all four frozen
hashes, and the unique test-function count. Hermes remains unauthorized.

## Reviewer publication

The reviewer publishes exactly:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/119_CEX002_LISTING_RESIDUAL_TEST_REVIEW.md`; and
- `tickets/CEX-002.md`.

No source/test path or unrelated dirty path belongs to the publication.

## Disposition

CEX-002 remains `IN_PROGRESS`. Gate 1 has not passed. Integration, tests, real candidate
execution, plan migration, sample acquisition, Gate 2, normalization, catalog publication,
Nautilus work, Harmonic Trader work, payoff analysis, PAPER, LIVE, and every other ticket
remain unauthorized. Next ticket remains `NONE`.
