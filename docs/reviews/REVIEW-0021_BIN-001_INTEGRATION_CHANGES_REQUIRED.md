# REVIEW-0021 - BIN-001 INTEGRATION: CHANGES_REQUIRED

**Ticket:** BIN-001 - Binance archive kline normalizer
**Integration reported at:** `ced2436`
**Status:** CHANGES_REQUIRED (integration evidence only)
**Next required actor:** Jr Dev - Hermes
**Date:** 2026-07-19

Direct inspection found no new production-source blocker requiring an immediate Sr Dev
revision. The v3 source addresses REVIEW-0020's source findings. Acceptance is withheld
because the Jr-owned regressions and change evidence do not yet establish all claimed
behavior.

## Findings

1. `test_no_network_used` hard-codes
   `/home/lars/Crypto_Multifactor_Bot/src/cryptofactors/ingest/binance.py`. The test is
   not portable to another checkout or CI path and violates the repository's no
   hard-coded-local-path rule.
2. The mixed-unit test checks only issue/status. It does not inspect both output rows to
   prove each was normalized with its own observed unit, despite its name and the
   REVIEW-0020 requirement.
3. Coverage is not asserted. The invalid-timestamp test checks an issue code but does
   not establish valid `CoverageWindow` bounds or that invalid times cannot corrupt
   those bounds.
4. Calendar tests exercise only `_parse_interval`; they do not test real monthly rows
   across variable month ends or a leap-year February as REVIEW-0020 required.
5. Market tests check column names but not physical values or partition unit metadata,
   and USD-M is not exercised. They therefore do not prove spot/USD-M/COIN-M volume
   semantics.
6. `test_full_man001_publish_plan` calls `verify_outputs` for both staged files but never
   calls `DatasetPublisher.publish`. It proves output verification, not successful
   MAN-001 publication of the returned plan.
7. The focused file contains 22 `test_*` functions while the change report claims 21
   regressions and 21 passes. The validation table also abbreviates rather than records
   the ticket-exact acceptance commands. Acceptance evidence must be internally
   consistent and traceable.

## Authorized integration task - Jr Dev - Hermes

Do not modify production source. Make the no-network test checkout-independent by
locating the imported module rather than embedding an absolute path. Strengthen focused
regressions to inspect mixed-unit output values; valid/invalid coverage; month-end and
leap-year monthly bars; spot, USD-M, and COIN-M physical volume values plus partition
units; and actual `DatasetPublisher.publish` of the complete bars-and-quality plan using
registered temporary raw dependencies. If the publication test exposes a production
defect, stop and report it without changing source so the reviewer can route Sr Dev.

Run every command from `tickets/BIN-001.md` exactly as written. Update
`BIN-001_CHANGE_REPORT.md` with the exact commands, actual collected test count, results,
and immutable integration commit evidence; commit and push; then stop for reviewer
inspection.

## Disposition

BIN-001 remains `IN_PROGRESS`. Sr Dev attention is not currently required. Next ticket
authorized: `NONE`.
