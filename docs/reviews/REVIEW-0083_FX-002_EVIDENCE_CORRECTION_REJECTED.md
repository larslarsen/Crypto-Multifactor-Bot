# REVIEW-0083 - FX-002 EVIDENCE CORRECTION REJECTED

**Ticket:** FX-002 - Stablecoin FX Source Feasibility Audit
**Status:** CHANGES_REQUIRED - EVIDENCE INCOMPLETE
**Next required actor:** Jr Dev - Hermes
**Next ticket authorized:** `NONE`
**Date:** 2026-07-21

## Decision

The `NONE` recommendation is directionally plausible, but the submitted audit does not prove it.
FX-002 remains open and all stablecoin-FX implementation remains unauthorized.

## Blocking Findings

1. `research/fx_002/EVIDENCE_REGISTER.csv` still contains placeholders and non-evidence:
   `07:xx`, `(error)`, `(to capture)`, `(external)`, approximate bounds, and generic licensing labels.
   This directly fails REVIEW-0082's exact evidence requirement.
2. The Coin Metrics note claims Community catalog and historical access require authentication. That
   contradicts accepted repository evidence in `research/sprint_003/sources/coin_metrics.md`, which
   records successful unauthenticated Community catalog and timeseries responses. The submitted
   audit neither inspects the actual stablecoin metric catalog nor establishes whether a qualifying
   USD metric exists.
3. The DefiLlama attempt uses `https://api.defillama.com/stablecoins`, not the repository-known
   official public endpoint `stablecoins.llama.fi/stablecoins?includePrices=true` recorded in
   `research/sprint_003/sources/defillama.md`. A zero-byte response from the wrong endpoint does not
   audit the candidate.
4. The Binance row explicitly says capture is still pending. The corresponding source note relies
   on an assertion and repository knowledge rather than an exact response or cited accepted artifact.
5. The Kraken recent-response record has no exact returned bounds, and the source note still labels
   the OHLC timestamp as bar close time. It is the bar interval timestamp; the report cannot assign
   close/publication semantics without provider evidence.
6. Licensing fields such as `Public` and `Community (limited)` are conclusions, not citations to
   captured terms or documentation.
7. The pytest record again uses hypothetical language: “usual warnings, no failures attributable”
   and “tests passed as before.” REVIEW-0082 explicitly required the actual observed result.
8. `README.md` and `docs/engineering/IMPLEMENTATION_BACKLOG.csv` still show accepted FX-001 readiness
   as `AWAITING_REVIEW`, so the requested repository-record reconciliation is incomplete.

## Required Action

Complete the bounded evidence work under
`docs/reviews/FX-002_JR_EVIDENCE_COMPLETION_TASK.md`. Do not begin another ticket.
