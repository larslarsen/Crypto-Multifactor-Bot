# FUND-002 - JR VERIFIABLE CLOSURE TASK

**Ticket:** `tickets/FUND-002.md`
**Actor:** Jr Dev - Hermes, fresh reliable execution required
**Status:** FAILED - REVIEW-0097
**Next ticket:** `NONE`

## Scope

Repair records without changing `NO_IMPLEMENTATION_AUTHORITY`. No implementation or broad research
is authorized. Network access is limited to one exact official USD-M documentation attempt:

`https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Get-Funding-Rate-History`

Capture its body and headers even if empty/error. Classify the existing COIN-M and legacy spot-doc
URLs as non-qualifying for USD-M semantics.

## Register Repair

- Give every body and header capture its own complete row with exact SHA-256, byte size, external
  path, retrieval UTC, HTTP status, and relationship to its request/body.
- Register `funding_listing.headers`, `updates.headers`, and all corresponding bodies.
- Register every empty/redirect/error documentation body with its actual hash and size.
- Correct sidecar metadata from each sidecar header file. In particular, BTCUSDT February sidecar
  ETag is `f00fbfdb979f43baa48fb461e04f22e1`; ETHUSDT January sidecar ETag is
  `412152171a26fca9add06dc3a24e1e73`.
- Keep REST interval `NOT_PRESENT`.
- Preserve the pinned README and separate 404 LICENSE evidence.
- Update report/source-note row counts and paths to the actual final register.

## Report Repair

- Restore `**Ticket:** FUND-002`.
- State exactly: four FAIL, two PARTIAL, one PASS, and one BLOCKED.
- Replace categorical ID-conflict wording with the accepted unresolved deterministic mapping contract
  between REF string IDs and integer fact surrogates.
- Replace all non-ASCII accidental wording.
- Record predecessor task statuses truthfully.
- Reconcile the source note with pinned README, LICENSE 404, correct USD-M docs attempt, and
  non-qualifying COIN-M/spot attempts.

## Mechanical Validation

Run a local CSV validation that fails unless every register row has the declared column count and
non-empty `request_id`, `url_or_request`, `kind`, `retrieved_utc`, `http_status`, `sha256`,
`compressed_bytes`, and `external_path`; hashes must be 64 lowercase hexadecimal characters and
sizes nonnegative integers. It must also verify every external path exists.

Record only the validator's literal PASS line and final evidence-row count in the report.

Then run a targeted text scan over the report/register/source note for:

- `Obtain или`
- `conflicts with accepted REF-001`
- `14 rows`
- the incomplete count phrase without `one BLOCKED`

The scan must return no matches. Record its no-match result and exit status.

## Governance And Acceptance

- Mark `FUND-002_JR_FINAL_EVIDENCE_INTEGRITY_TASK.md` `FAILED - REVIEW-0096`.
- Mark this task complete only after validations pass.
- Set ticket, report, README, backlog, and handoff to `AWAITING_REVIEW`; name Reviewer as next actor;
  retain `Next ticket authorized: NONE`.
- Run `python3 scripts/check_repo_control.py` and record the literal PASS result.
- Commit, push, and stop. No pytest run is required. Do not begin another ticket.
