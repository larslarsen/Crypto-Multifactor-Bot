# REVIEW-0233 - DATA-007 REOPENED, CHANGES REQUIRED

**Ticket:** DATA-007 - Free DEX/CEX Source Capability & Rate-Limit Probe
**Decision:** CHANGES_REQUIRED
**Reviewer:** Lead Quantitative Finance Researcher/Engineer
**Date:** 2026-07-26

## Reason for reopening

REVIEW-0211 accepted DATA-007 on the representation that CI network calls were
mocked. Repository-wide verification during REVIEW-0232 disproved that premise.

`GeckoTerminalProbe`, `DexScreenerProbe`, `DefiLlamaProbe`, `BinancePublicProbe`,
and `BitmexFundingProbe` accept a `mock` client but pass `mock=None` to
`_request_or_mock()` in their live branches. The parametrized mock test therefore
contacts public endpoints. Its result depends on current provider availability:
GeckoTerminal and Binance returned `partial` during review, producing two failures.

This violates DATA-007's requirement that CI use mocks with no network access and
makes the repository-wide suite nondeterministic.

## Required correction

1. Route each supplied mock client through all five affected live probe paths.
2. Keep actual live behavior unchanged when no mock is supplied.
3. Make the existing parametrized test prove that every probe used its supplied
   `MockTransport`; no public endpoint may be contacted by the test suite.
4. Run the DATA-007 test file, the complete suite, scoped Ruff, and repository
   control. Record exact outcomes.

## Scope

- No changes to the accepted matrix artifact or its research conclusions.
- No new providers, backfills, paid sources, Birdeye OHLCV, or LIVE authority.
- Do not begin DATA-008, DATA-009, or DEX-002.

## Next

- **Next required actor:** Sr Dev - Claude Sonnet 5
- **Next ticket authorized:** NONE
