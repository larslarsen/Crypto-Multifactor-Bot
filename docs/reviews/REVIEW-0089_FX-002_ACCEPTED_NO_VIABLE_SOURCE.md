# REVIEW-0089 - FX-002 ACCEPTED: NO VIABLE PRIMARY SOURCE

**Ticket:** FX-002 - Stablecoin FX Source Feasibility Audit
**Status:** ACCEPTED - IMPLEMENTATION REMAINS BLOCKED
**Next required actor:** Jr Dev - Hermes, acceptance publication only
**Next ticket authorized:** `NONE`
**Date:** 2026-07-21

## Decision

FX-002 is accepted with `Recommendation: NONE`. No evaluated candidate passes all mandatory direct
USD, historical depeg, point-in-time availability, revision, reproducibility, and licensing gates.

This acceptance closes the feasibility audit only. It does not authorize an FX schema, ADR,
migration, normalizer, join, generated dataset, or downstream stablecoin-to-USD conversion.

## Accepted Source Findings

- Kraken `USDTZUSD` is directionally valid, but REST ignores old `since` values beyond its recent
  capped window. Historical depeg coverage, availability semantics, revisions, and licensing do not
  pass.
- Coin Metrics Community asset-metric availability could not be audited from the observed
  unauthorized response. No qualifying USD reference-rate series is established.
- DefiLlama's observed stablecoin payload is a current snapshot and does not establish historical
  point-in-time prices.
- Binance currently exposes direct `USDTUSD` and `USDCUSD` spot instruments and recent official
  archive objects with matching provider checksums. Correct May 2022 archive objects are absent, and
  fiat semantics, availability, revisions, and licensing remain unknown. It therefore cannot serve
  as the required historical primary.

## Acceptance Evidence

- Both REVIEW-0088 preflight scans: no matches, exit status 1.
- Repository control: `Repo control check: PASS`.
- Required pytest invocation: effective `-qq`, exit status 0.
- Supplementary single-quiet suite: `449 passed, 1 warning in 19.49s`, exit status 0.
- Provider raw payloads remain outside the repository under `/tmp/fx_002_raw`; repository artifacts
  contain hashes and analytical metadata only.

## Publication

Jr Dev - Hermes owns accepted-state publication under
`docs/reviews/FX-002_JR_ACCEPTANCE_PUBLICATION_TASK.md`. No next ticket is authorized.
