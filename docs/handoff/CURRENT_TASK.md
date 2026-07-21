# CURRENT_TASK

Ticket: AUD-004
State: AWAITING_REVIEW
Next ticket authorized: NONE
Next required actor: Reviewer

Accepted dependency: AUD-002 (`ACCEPTED` at `899fb7c802dc4ba9b951118598417aef6d22cdcb`).
Governing documents:
- tickets/AUD-004.md
- docs/reviews/REVIEW-0007_AUD-002_FINAL.md
- docs/reviews/REVIEW-0006_AUD-002_INTEGRATION.md
- research/sprint_003/13_RESEARCH_LEAD_DECISIONS.md
- research/sprint_003/12_AUDIT_EXECUTION.md (headerless precision failure / adapter evidence)

## Authorized work

Add native headerless support to `source_audit.compare_binance_archive_precision` so the
adjacent-archive precision-transition check runs on real Binance daily dumps (aggTrades / klines),
which are headerless CSVs. Preserve the existing explicit minimum-evidence and quality thresholds.
Add focused tests covering headerless aggTrades/klines precision pairs. Document the headerless
invocation path.

Do not modify production behavior outside the headerless path. Do not bypass existing thresholds.
AUD-004 is non-blocking for RAW-001.

## Stop condition

After the acceptance commands pass, produce a change report and stop. Do not begin the next ticket.
