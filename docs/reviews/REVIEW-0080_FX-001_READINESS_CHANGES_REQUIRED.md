# REVIEW-0080 - FX-001 READINESS CHANGES REQUIRED

**Ticket:** FX-001 - Point-in-Time Stablecoin FX Readiness
**Status:** CHANGES_REQUIRED - JR RECORDS AND ANALYSIS ONLY
**Next required actor:** Jr Dev - Hermes
**Next ticket authorized:** `NONE`
**Date:** 2026-07-20

## Decision

FX-001 remains implementation-blocked. The first readiness report identifies the core P0 gap but
does not provide the exact repository-grounded contract required for an engineering decision.

## Findings

1. The proposed schema is not typed or deterministic. It uses alternatives such as “surrogate or
   hash,” “boolean or severity,” and “confidence class or quality flag,” with no nullability,
   precision, units, keys, canonical sort, partition path, or identity body.
2. Existing contracts are omitted. REF-001 already defines `AssetClass.FIAT` and
   `AssetClass.STABLE`, plus base/quote asset IDs. The catalog publisher already accepts a generic
   string `dataset_type`; absence of an FX-specific SQLite table does not imply observations belong
   in SQLite.
3. A proposed `fx_observation` SQL table conflicts with the frozen boundary that SQLite stores
   control metadata, not large price/funding/FX observations. Any migration need must be justified
   as control-plane metadata not already represented by generic dataset manifests.
4. Source statuses are inaccurate or overclaimed. Coin Metrics is conditional reference metadata,
   not simply deferred; DefiLlama’s audited endpoint is a current-biased stablecoin asset/supply
   family with unresolved PIT/revision suitability and no “CC0-ish” evidence; exchange documentation
   establishes no repository-accepted FX source, not that exchanges categorically have “no FX.”
5. The implementation split combines source acquisition, canonical schema, normalization, and
   downstream joining. It does not select one smallest next step.
6. Gate commands are placeholders rather than exact commands.

## Required Correction

Jr Dev - Hermes must replace the report with exact repository facts and one unambiguous
recommendation under `docs/reviews/FX-001_JR_READINESS_CORRECTION_TASK.md`. No implementation,
provider access, ADR, migration, or architecture edit is authorized.
