# FUND-002 — Binance Funding Source Semantics Audit Report

**Ticket:** FUND-002
**Status:** AWAITING_REVIEW
**Next ticket authorized:** `NONE`
**Next required actor:** Reviewer
**Date:** 2026-07-21

## Recommendation
**NO_IMPLEMENTATION_AUTHORITY**

All eight semantic gates were evaluated against exact captured evidence. Four gates fail, two are partial,
and one passes. Under the fail-closed rule, any unknown mandatory semantic yields `NO_IMPLEMENTATION_AUTHORITY`.

Decisive blockers:
- `calc_time` is a 13-digit ms UTC epoch in every sampled row, and REST `fundingTime` matches.
  The captured README and listing/docs do not classify whether it marks scheduled funding settlement,
  mark-price time, or another boundary. This is mandatory for point-in-time canonical publication.
- `last_funding_rate` is numeric decimal positive in all sampled rows, and REST `fundingRate` matches.
  Provider unit, sign/payer convention, and formula semantics are not documented in captured evidence.
- Provider `.CHECKSUM` sidecars match all three sampled ZIPs exactly. That proves download integrity.
  Funding-specific replacement register and correction policy are not demonstrated in captured evidence.
- Captured README states `Licence: MIT` for the repository. Exact redistribution terms for funding archive
  metadata/hashes are not further established by this capture.

## 1. Source-Semantics Audit Summary

Sources only: official Binance USD-M fundingRATE archive (`data.binance.vision/data/futures/um/monthly/fundingRate`) and official live REST (`fapi.binance.com/fapi/v1/fundingRate`). No implementation, schema, migration, ADR, factor, portfolio, or USD-conversion work is authorized.

### calc_time
- Observed: 13-digit integer UTC epoch milliseconds in all three monthly archives.
- BTCUSDT 2025-01 range: 1735689600015 through 1738339200000.
- BTCUSDT 2025-02 range: 1738368000000 through 1740758400000.
- ETHUSDT 2025-01 range: 1735689600015 through 1738339200000.
- REST `fundingTime` field also presents 13-digit ms epoch (matched: 1784534400001, 1784563200004,
  1784592000001, 1784620800000, 1784649600002).
- Official documentation: not captured. No official doc body proves whether `calc_time` equals funding event
  start, mark-price time, settlement transfer, or provider bookkeeping timestamp.

### funding_interval_hours
- Observed: `8` in every row of all three monthly archives.
- REST does not return interval field.
- Official documentation: README documents kline/aggTrade/trade families but no funding interval semantics.
  Other instruments/years are outside this bounded audit.

### last_funding_rate
- Observed: numeric decimal values positive in all samples (e.g., `0.00010000`, `0.00008098`, `0.00005369`).
- REST `fundingRate` also positive decimal, matched: `0.00005278`, `0.00006518`, `0.00005400`.
- Official documentation: not captured. Unit, positive/negative payer/receiver convention, and formula are
  not established.

### Availability
- Archive objects carry HTTP `Last-Modified: Sun, 16 Feb 2025 12:52:38 GMT` for Jan files and
  `Sun, 16 Mar 2025 13:03:19 GMT` for Feb files. This is the provider's historical publication-bound evidence.
- Local retrieval time `2026-07-21` cannot make these rows available to prior strategy decisions.
- Strategy availability must use `availability_time <= decision_time` semantics; provider publication time must
  be separate and defensible beyond listing-headers.

### Corrections / Replacement
- Provider `.CHECKSUM` sidecars match all three sampled ZIPs and sidecars exactly (verified against local
  SHA-256 for FUND002-R01..R06).
- Provider ETag headers present on archive and sidecar responses.
- Funding-specific replacement register/policy is not demonstrated in captured evidence despite README
  generic statement "archived files may be updated". Do not project the aggregate-trade replacement
  behavior onto funding archives; it requires explicit provider evidence.
- `x-amz-server-side-encryption: AES256` is server-side storage encryption metadata; it is not
  a hash space or lineage identifier and is excluded from raw/manifest reasoning.

### Licensing
- Official documentation: captured README states `Licence: MIT` for the repository.
- Exact redistribution terms for funding archive metadata/hashes are not further established by this capture.
- Prior `research/sprint_003/sources/binance.md` records: "Public market data usable for research;
  confirm redistribution terms before committing raw data."

### Lineage
- Raw bytes identified by provider SHA-256 checksum and ETag.
- External raw path: `/tmp/fund_002_raw/docs/*.zip` and sidecars.
- Manifest dataset_id lineage: archive zip → raw object → dataset manifest → normalized event dataset.
- Dataset version + supersession relationship defined by MAN-001 and RAW-002.
- AES256 server-side storage encryption is excluded from lineage reasoning.

## 2. Semantic Gate Results

The complete, re-evaluated gate results are in `research/fund_002/decision_matrix.csv` and are reproduced
here for review:

| Gate | gate_label | Status | Blocking |
|---|---|---|---|
| G01 | calc_time event classification | FAIL | Yes |
| G02 | interval unit and effective scope | PARTIAL | Yes |
| G03 | rate unit/sign/formula | FAIL | Yes |
| G04 | provider publication / availability | PARTIAL | Yes |
| G05 | funding-specific checksum and replacement | FAIL | Yes |
| G06 | licensing / redistribution | FAIL | Yes |
| G07 | raw and manifest lineage | PASS | No |
| G08 | stablecoin-FX rule | BLOCKED | N/A |

Fail-closed rule applies: one failing mandatory gate prevents canonical publication.

## 3. Existing Schema Critique

The repo draft `schemas/funding_cashflow.schema.json` names the dataset `funding_cashflows` and uses
integer `instrument_id` and string `venue_id`. The integer `instrument_id` conflicts with accepted REF-001
string surrogate IDs. More importantly, the schema conflates event and realized-cashflow semantics by naming
the dataset `funding_cashflows` while including `long_cashflow_sign` without notional, settlement, price
basis, or sign-formula inputs. This audit cannot accept that dataset type name.

A later source normalizer may emit `funding_rate_event` only after source semantics pass and the dataset
name is reviewed.

## 4. Follow-up After Gate Passes

No implementation test matrix is authorized because readiness fails. If the blockers are resolved:

1. Obtain или capture official Binance documentation proving `calc_time` meaning.
2. Capture rate unit/sign/formula documentation for USD-M perpetual.
3. Prove funding-specific replacement/correction applicability.
4. Capture exact redistribution terms.
5. Then propose a bounded implementation ticket or `IMPLEMENTATION_READINESS`.

## 5. Unknowns That Must Remain Unknown
- Whether `calc_time` equals settlement transfer time.
- Rate payer/receiver sign convention across instruments.
- Formula basis (mark-price-tied vs index-price-tied settlement).
- Historical replacement behavior for funding archives.

These unknowns are not inventions; they are fail-closed blockers until source evidence exists.

## 7. Records and State Transition

- `tickets/FUND-002.md`: set to `AWAITING_REVIEW`, recommendation `NO_IMPLEMENTATION_AUTHORITY`.
- `docs/reviews/FUND-002_SOURCE_SEMANTICS_REPORT.md`: this document.
- `research/fund_002/EVIDENCE_REGISTER.csv`: complete evidence register (14 rows, 21 columns).
- `research/fund_002/decision_matrix.csv`: eight-gate classification with recommendation.
- `research/fund_002/sources/binance.md`: source note for Binance funding family.
- `docs/reviews/FUND-002_JR_SOURCE_SEMANTICS_AUDIT_TASK.md`:COMPLETED.
- `docs/reviews/FUND-002_JR_EVIDENCE_REGISTRATION_CORRECTION_TASK.md`:COMPLETED.
- `docs/engineering/IMPLEMENTATION_BACKLOG.csv`: FUND-002 `AWAITING_REVIEW`.
- `README.md`: FUND-002 listed as `AWAITING_REVIEW`.
- `docs/handoff/CURRENT_TASK.md`: next actor `Reviewer`, next ticket `NONE`.

## 8. Acceptance Command Evidence

`python3 scripts/check_repo_control.py`
Repo control check: PASS

----

**Note on external-page limitations:** listing-page bodies under `data.binance.vision/.../fundingRate/BTCUSDT/`
returned minimal/placeholder content in this environment. Available alternatives (live REST, archive ZIPs,
response headers, provider `.CHECKSUM`, ETag, file `Last-Modified`, prior local binance.md sprint note,
accepted aggregate-trade replacement evidence) are included in the evidence register. Do not invent
doc semantics from absent page content.
