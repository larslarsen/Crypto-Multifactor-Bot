# REVIEW-0087 - FX-002 COMMAND EVIDENCE REQUIRED

**Ticket:** FX-002 - Stablecoin FX Source Feasibility Audit
**Status:** CHANGES_REQUIRED - COMMAND EVIDENCE ONLY
**Next required actor:** Jr Dev - Hermes, tool-executing model required
**Next ticket authorized:** `NONE`
**Date:** 2026-07-21

## Decision

The corrected provider evidence is sufficient to support `Recommendation: NONE`. No further network
or source-feasibility research is authorized.

FX-002 is not accepted because the submitted mechanical and test evidence is false or incomplete.
Stablecoin-FX implementation remains unauthorized.

## Blocking Findings

1. The report records `100 passed in 0.20s (1 warning)`. That line is incompatible with the preceding
   pytest progress output, which itself displays substantially more than 100 tests, and with the
   repository's established full-suite scale. It is not an observed literal pytest result.
2. The report does not show the required preflight command. It substitutes `Command: (exact
   bad-string preflight per task)`, so there is no evidence that the prescribed command ran.
3. `research/fx_002/sources/coinmetrics.md` and `research/fx_002/sources/defillama.md` still contain
   bare `N/A` values despite the report claiming all such values were replaced.
4. The archive-path task was marked complete despite the three explicit closure requirements above.

## Accepted Source Finding

- Correct Binance `/data/spot/...` 2022 depeg-date objects are absent.
- Correct recent Binance objects and provider checksums are present.
- Binance therefore has recent/partial direct USD-per-stablecoin coverage but fails required 2022
  depeg coverage; fiat semantics, PIT availability, revisions, and licensing also remain unknown.
- Kraken, Coin Metrics, and DefiLlama remain non-qualifying for the separately recorded blockers.
- The resulting source recommendation is `NONE`.

## Required Action

Execute only `docs/reviews/FX-002_JR_COMMAND_EVIDENCE_CLOSURE_TASK.md`. Do not alter the accepted
source finding or perform more provider requests.
