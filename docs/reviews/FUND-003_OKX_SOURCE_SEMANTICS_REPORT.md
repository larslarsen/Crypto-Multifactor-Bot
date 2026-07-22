# FUND-003 — OKX Funding Archive Source Semantics Audit Report

**Status:** ACCEPTED - REVIEW-0110
**Next ticket authorized:** `NONE`
**Next required actor:** Reviewer
**Date:** 2026-07-21 (corrected under REVIEW-0106, REVIEW-0107, REVIEW-0108, REVIEW-0109)

## Recommendation
**NO_IMPLEMENTATION_AUTHORITY**

Six gates fail/partial-fail closed: G02 (archive rate predicted/realized distinction, PARTIAL, blocking),
G03 (formulaType scope + transition boundary, FAIL), G04 (interval derivation + variable-interval rules,
PARTIAL, blocking), G05 (replacement/correction policy, FAIL), G07 (licensing ambiguity for intended
internal use, FAIL), G08 (full request identity, FAIL). G01 PASS, G06 PASS with conservative 2026
availability bound.

## Evidence Summary

All evidence preserved outside Git under `/tmp/opencode/source_recheck_20260721/` (retained) and
`/tmp/okx_cap/` (re-fetched / newly captured). Committing only metadata, hashes, findings, and
repository control records. EVIDENCE_REGISTER.csv separates response bodies (B) and headers (H),
records exact request URLs, and corrects all hashes/sizes/row counts/timestamp bounds/interval sets/
ETags/Last-Modified/HTTP statuses. Exact POST request bodies for R08–R10 were NOT retained (stated
literally, not claimed as captured).

## Gate Results

| Gate | Label | Status | Blocking |
|---|---|---|---|
| G01 | fundingTime event/settlement semantics | PASS | No |
| G02 | archive rate predicted-vs-realized distinction | PARTIAL | Yes |
| G03 | formulaType scope + transition boundary | FAIL | Yes |
| G04 | interval derivation + variable-interval rules | PARTIAL | Yes |
| G05 | archive integrity + replacement/correction policy | FAIL | Yes |
| G06 | publication/backfill availability | PASS | No |
| G07 | licensing/terms (intended internal scope) | FAIL | Yes |
| G08 | immutable raw lineage (full request identity) | FAIL | Yes |

## Key Findings

### G01 — fundingTime semantics (PASS)
- `fundingTime` documented as settlement time in Unix milliseconds (REST docs: "Settlement time,
  Unix timestamp format in milliseconds"). REST sample confirms e.g. `1784649600000`.
- Availability is judged under G06, not here.

### G02 — archive rate distinction (PARTIAL/FAIL, blocking)
- Archive CSV schema: `instrument_name,funding_rate,funding_time` — single rate column.
- Provider REST distinguishes `fundingRate` (predicted) vs `realizedRate` (actual settled), but this
  distinction is NOT present in the archive schema. The archive `funding_rate` cannot be officially
  classified as predicted or realized without a documented mapping. Under-specified.

### G03 — formulaType and transition (FAIL)
- Archive CSV has no `formulaType` column.
- Official announcement (RFA) states the new formula rolled out in 3 batches from April 10, 2025, but
  no archive carries the field, so the boundary cannot be verified from archive data.
- Changelog (RCL) 2025-04-28 entry is AWS-domain cessation, not the formula transition.
- BTC transition-boundary archives around April 24, 2025 were NOT acquired in this audit.
  Transition-boundary verification incomplete.

### G04 — Interval derivation (PARTIAL, blocking)
- 2026-07-19 archive distribution (by funding_time differences): 231 instruments at 8h, 194 at 4h,
  **1 at 2h**, **1 at 1h**.
- Mechanism article (R06B): cycles are 1h / 2h / 4h / 8h. API documentation (R04B) additionally
  mentions a possible 6h adjustment ("may be adjusted to higher frequencies such as 6 hours, 4 hours,
  2 hours, or 1 hour"). Use fundingTime/nextFundingTime difference.
- Missing formal rules: adjacent-event handling, cross-day boundaries, tolerance for interval
  jitter, and frequency-transition encoding (how a 4h→8h switch is recorded). PARTIAL and blocking.

### G05 — Integrity and replacement (FAIL)
- ETag/Content-MD5 verify current-object bytes for R01/R02/R12 (integrity PASS).
- Provider replacement/correction behavior is undocumented.
- R01 Last-Modified 2026-02-02 and R12 Last-Modified 2025-12-17 date the current
  representations. They cannot distinguish initial backfill from replacement. Replacement/correction
  behavior unknown.

### G06 — Availability (PASS with 2026 bound)
- Historical endpoint exists; R05 confirms module 3. Its introduction date is not stated on the landing page.
- Availability passes only with a conservative 2026 bound based on the audit/acquisition context.
- Do not claim 2022 availability; R01 provides no proof of 2022 publication.
- BTC transition-boundary archives around April 24, 2025 were not acquired in this audit.

### G07 — Licensing (FAIL, intended internal scope)
- Evaluated strictly against intended internal research use: acquisition of publicly available
  funding data and retention of metadata/hashes for internal non-commercial research.
- OKX API Agreement §9.4 restricts Market Data to non-commercial use and prohibits redistribution.
- Internal acquisition and metadata retention are within permitted non-commercial scope; redistribution
  is outside this gate and was not attempted.
- However, whether §9.4's non-commercial restriction permits this specific internal research
  acquisition unambiguously is not expressly stated — gate FAILS on that ambiguity, not on absence of
  redistribution rights.

### G08 — Raw lineage (FAIL until full identity)
- Register rebuilt with bodies/headers separated, exact URLs, corrected hashes/sizes/row counts/
  timestamp bounds/interval sets/ETags/Last-Modified/HTTP statuses.
- R08–R10 are POST `download-link` responses; exact POST request bodies were NOT retained and re-fetch
  returns 429/param errors, so request identity for those rows is incomplete.
- FAIL until exact request bodies captured; do not claim they were captured.

## Recommendation

**NO_IMPLEMENTATION_AUTHORITY** — fail-closed on G02 (partial, blocking), G03 (fail), G04 (partial,
blocking), G05 (fail), G07 (fail), G08 (fail). Settlement semantics (G01), interval distribution (G04
partial), and 2026 availability (G06) are documented but insufficient for implementation authority.

Even a passing audit cannot authorize realized funding-cashflow, portfolio, CARRY, USD-conversion,
schema, ADR, migration, or production work.
