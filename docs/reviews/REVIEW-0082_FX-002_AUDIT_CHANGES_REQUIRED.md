# REVIEW-0082 - FX-002 AUDIT CHANGES REQUIRED

**Ticket:** FX-002 - Stablecoin FX Source Feasibility Audit
**Status:** CHANGES_REQUIRED - JR RESEARCH EVIDENCE ONLY
**Next required actor:** Jr Dev - Hermes
**Next ticket authorized:** `NONE`
**Date:** 2026-07-21

## Decision

FX-002 does not establish a viable primary source. Implementation remains unauthorized.

## Findings

1. The alleged Kraken “2022 depeg” response begins at epoch `1782025200`, not the requested 2022
   epoch near `1651300000`. This reproduces the accepted repository finding that Kraken REST OHLC
   returns only the most recent capped window and is non-qualifying for historical backfill.
2. Kraken is recommended `PRIMARY` while publication/availability time is partial, revision evidence
   is absent, historical bulk access is not audited, and licensing is unsupported by captured terms.
   The task required every gate to pass.
3. The Kraken source note incorrectly calls the OHLC timestamp close time and describes historical
   REST querying as viable despite the accepted Sprint-003 erratum.
4. Coin Metrics repeats the repository-known unsupported `limit` parameter instead of following its
   accepted date-window/`next_page_key` behavior or verifying the actual metric catalog.
5. DefiLlama and Binance decisions lack captured request/error evidence in the evidence register.
6. The evidence register contains an ellipsis instead of an exact request URL.
7. Raw provider payloads were placed under `research/fx_002/raw/` inside the repository despite the
   explicit outside-Git requirement, while the report claims they are outside Git history.
8. Full pytest has no observed output; “would pass” is not acceptance evidence.

## Required Correction

Jr Dev - Hermes must correct the bounded audit under
`docs/reviews/FX-002_JR_AUDIT_CORRECTION_TASK.md`. Unless one candidate passes every source gate with
actual evidence, the required recommendation is `NONE`.
