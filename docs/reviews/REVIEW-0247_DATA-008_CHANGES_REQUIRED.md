# REVIEW-0247 - DATA-008 CHANGES REQUIRED

**Ticket:** DATA-008 - Free CEX Universe Expansion (Binance-first)
**Decision:** CHANGES_REQUIRED
**Reviewer:** Lead Quantitative Finance Researcher/Engineer - Sol 5.6 High
**Date:** 2026-07-27

## Findings

1. **High - production code identity still has a public bypass.** The runner exposes
   `--skip-identity-check`, and tests use that production CLI flag. Any controlled
   operator can therefore publish an arbitrary `--code-commit`, recreating the false
   lineage path REVIEW-0245 required removing. Delete the CLI bypass and make tests
   monkeypatch/inject the verifier through a non-production test seam.
2. **High - out-of-range successful history timestamps still escape typed failure.**
   `parse_first_kline_open_time()` validates finite whole milliseconds but calls
   `datetime.fromtimestamp()` without converting its `OverflowError`, `OSError`, or
   `ValueError` into `BinanceUniverseError`. A huge integer therefore aborts outside
   `HISTORY_REQUEST_FAILED` rather than remaining pending with auditable failure
   evidence. Add a huge-integer regression and normalize conversion failures.

## Closed

The REVIEW-0246 source corrections are otherwise present locally: reconciled
`ALREADY_CURRENT` cursor advancement, strict close classification, malformed-history
handling, distinct failed/deferred reporting, versioned policy/provider queue identity,
actual trade aggregation, and clean-source identity verification. Report 36 reflects
policy `2026-07-27.2` and actual trade counts.

## Verification

Review was intentionally limited to targeted local-file inspection per owner token-use
policy. No Git, test, lint, catalog, or repository-control commands were run. Jr Dev
owns those checks after integrating the two corrections.

## Routing

- **Next required actor:** Sr Dev - Grok Build
- **Final reviewer:** Sol 5.6 High
- **Next ticket authorized:** NONE
