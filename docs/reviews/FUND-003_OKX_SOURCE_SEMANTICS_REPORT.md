# FUND-003 — OKX Funding Archive Source Semantics Audit Report

**Status:** AWAITING_REVIEW
**Next ticket authorized:** `NONE`
**Next required actor:** Reviewer
**Date:** 2026-07-21 (corrected under REVIEW-0106)

## Recommendation
**NO_IMPLEMENTATION_AUTHORITY**

Five gates fail/partial-fail closed: G02 (archive rate predicted/realized distinction, PARTIAL),
G03 (formulaType scope + transition boundary, FAIL), G05 (replacement/correction policy, FAIL),
G07 (redistribution terms, FAIL), G08 (full request identity, FAIL). G01 PASS, G04 PARTIAL,
G06 PASS with conservative 2026 availability bound.

## Evidence Summary

All evidence preserved outside Git under `/tmp/opencode/source_recheck_20260721/` (retained) and
`/tmp/okx_cap/` (re-fetched / newly captured). Committing only metadata, hashes, findings, and
repository control records. EVIDENCE_REGISTER.csv separates response bodies (B) and headers (H),
records exact request URLs, and (where retained) exact POST bodies.

## Gate Results

| Gate | Label | Status | Blocking |
|---|---|---|---|
| G01 | fundingTime event/settlement semantics | PASS | No |
| G02 | archive rate predicted-vs-realized distinction | PARTIAL | Yes |
| G03 | formulaType scope + transition boundary | FAIL | Yes |
| G04 | interval derivation + variable-interval rules | PARTIAL | Yes |
| G05 | archive integrity + replacement/correction policy | FAIL | Yes |
| G06 | publication/backfill availability | PASS | No |
| G07 | licensing/terms (literal internal scope) | FAIL | Yes |
| G08 | immutable raw lineage (full request identity) | FAIL | Yes |

## Key Findings

### G01 — fundingTime semantics (PASS)
- `fundingTime` documented as settlement time in Unix milliseconds (REST docs: "Settlement time,
  Unix timestamp format in milliseconds"). REST sample confirms e.g. `1784649600000`.
- Availability is judged under G06, not here.

### G02 — archive rate distinction (PARTIAL/FAIL)
- Archive CSV schema: `instrument_name,funding_rate,funding_time` — single rate column.
- Provider REST distinguishes `fundingRate` (predicted) vs `realizedRate` (actual settled), but
  this distinction is NOT present in the archive schema. The archive `funding_rate` cannot be
  officially classified as predicted or realized without a documented mapping. Under-specified.

### G03 — formulaType and transition (FAIL)
- Archive CSV has no `formulaType` column.
- REST docs define `noRate` (old formula) / `withRate` (new formula), but no archive carries the
  field, so the April-2025 transition boundary cannot be verified from archives.
- No official dated formula-change announcement captured (API docs and help articles describe the
  fields but not the transition event). Transition-boundary verification incomplete.

### G04 — Interval derivation (PARTIAL)
- 2026-07-19 archive distribution (by funding_time differences): 231 instruments at 8h, 194 at 4h,
  **1 at 2h**, **1 at 1h** (e.g. 0G-USDT-SWAP at 4h; one 2h and one 1h instrument confirmed).
- Docs: default 8h; variable 6h/4h/2h/1h for volatile altcoins; use fundingTime/nextFundingTime
  difference.
- Missing formal rules: adjacent-event handling, cross-day boundaries, tolerance for interval
  jitter, and frequency-transition encoding (how a 4h→8h switch is recorded). PARTIAL.

### G05 — Integrity and replacement (FAIL)
- ETag/Content-MD5 verify current-object bytes for R01/R02/R12 (integrity PASS).
- Provider replacement/correction behavior is undocumented.
- R01 object Last-Modified `2026-02-02` and R12 object Last-Modified `2025-12-17` show objects were
  replaced after their archive dates, but **Last-Modified alone does NOT prove replacement semantics
  or provide a correction/changelog policy**. Replacement/correction behavior unknown.

### G06 — Availability (PASS with 2026 bound)
- Historical endpoint introduced September 2025.
- PASS only with conservative **2026 availability bound**: R02 (2026-07-19) and R12 (2025-04-15)
  objects are post-endpoint. **Do NOT claim 2022 availability** — R01 Last-Modified is 2026-02-02
  with no proof of 2022 publication.

### G07 — Licensing (FAIL)
- OKX API Agreement §9.4 "Market Data — Non-Commercial Use and Redistribution Restrictions"
  restricts Market Data to non-commercial use and prohibits redistribution.
- Literal internal scope: research acquisition and metadata retention for internal non-commercial
  use are within permitted scope; **redistribution is prohibited**. No commercial license. Gate
  fails on the redistribution restriction (no "fair use" substitution; commercial redistribution is
  explicitly out of scope).

### G08 — Raw lineage (FAIL until full identity)
- Register rebuilt with bodies/headers separated, exact URLs, corrected hashes/sizes/row counts/
  timestamp bounds/interval sets/ETags/Last-Modified/HTTP statuses.
- R08–R10 are POST `download-link` responses; exact POST request bodies were NOT retained and
  re-fetch returns 429/param errors, so request identity for those rows is incomplete.
- FAIL until all registered identities match retained evidence; reassess after exact request bodies
  are captured.

## Recommendation

**NO_IMPLEMENTATION_AUTHORITY** — fail-closed on G02 (partial), G03 (fail), G05 (fail), G07 (fail),
G08 (fail). Settlement semantics (G01), interval distribution (G04 partial), and 2026 availability
(G06) are documented but insufficient for implementation authority.

Even a passing audit cannot authorize realized funding-cashflow, portfolio, CARRY, USD-conversion,
schema, ADR, migration, or production work.
