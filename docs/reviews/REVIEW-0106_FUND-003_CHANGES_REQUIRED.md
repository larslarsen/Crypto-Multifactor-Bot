# REVIEW-0106 — FUND-003 CHANGES REQUIRED

**Reviewed commit:** 82c27f52cdecdc2a39669da4dde91276f92228a6
**Decision:** CHANGES_REQUIRED
**Next ticket authorized:** NONE
**Date:** 2026-07-21

## Defects Identified

1. **Evidence register structural defect** — bodies and response headers were conflated in a single
   row; exact request URLs and POST request bodies were not recorded; several hash/byte/row/timestamp/
   interval/ETag/Last-Modified/HTTP-status values were wrong.
2. **Missing official evidence** — no April 2025 archive samples at the BTC formula transition, no
   official formula-change announcement, no final funding-mechanism article capture (R06 was a 301
   redirect stub), no OKX API Agreement capture, no API changelog, no exact historical-data request
   bodies, no exact REST funding-history request + headers.
3. **Gate matrix defects** — G01 mislabeled availability as a semantics failure; G02 overstated
   archive rate semantics; G03 overstated transition verification; G04 under-specified interval
   distribution and rules; G05 over-claimed from Last-Modified; G06 over-claimed 2022 availability;
   G07 used "fair use" framing instead of literal internal research scope; G08 was PASS with
   unmatched identities.
4. **Dependency defect** — FUND-003 dependency listed as FUND-001 but ticket text said FEE-001.
5. **Backlog line-ending defect** — CRLF line endings caused `git diff --check` to flag trailing CR.

## Corrective Actions

- REVIEW-0106 created (this document).
- EVIDENCE_REGISTER.csv rebuilt with bodies and headers in separate rows, exact request URLs, exact
  POST bodies recorded, all hashes/sizes/row counts/timestamp bounds/interval sets/ETags/Last-Modified
  values/HTTP statuses corrected against retained bytes and re-fetched captures. `superseded_by` left
  empty (no row genuinely replaces another; R06 redirect is distinct from R06b mechanism article).
- Missing evidence captured: April 2025 archive samples (2025-04-15, 2025-04-20), final funding-
  mechanism article (R06b), OKX API Agreement (R11), re-fetched REST funding-history with exact
  request + headers (R03 rebuilt), April-2025 archive object headers (R12).
- Decision matrix corrected per gate-by-gate instructions.
- Recommendation retained: NO_IMPLEMENTATION_AUTHORITY with corrected blocking gates
  (G02 partial, G03 fail, G05 fail, G06 pass-with-bound, G07 fail, G08 reassessed).
- Ticket dependency corrected to FUND-001.
- IMPLEMENTATION_BACKLOG.csv line endings normalized to LF.
- CURRENT_TASK, README, backlog, ticket, report set to AWAITING_REVIEW / Reviewer / NONE.

## Status

CHANGES_REQUIRED — published as a new corrective commit (not an amend of 82c27f5).
