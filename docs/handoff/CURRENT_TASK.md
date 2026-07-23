# CURRENT_TASK

Ticket: AUD-006
State: READY
Next required actor: Sr Dev (Strong Model) — perform the execution risk audit
Next ticket authorized: AUD-006

**Reviewer Decision (Architecture & Ticket Selection):**
We have completed Sequence #25 (Paper Execution Runtime). According to `IMPLEMENTATION_SEQUENCE.md`, Sequence #26 (Live Execution Routing) requires an explicit risk-board authorization.

Before we write any code that touches live exchange APIs or loads real API keys, we must formally audit the execution and promotion gates to ensure live trading cannot be accidentally triggered by research or paper artifacts.

I am drafting and authorizing **AUD-006** (Execution Risk & Live Authority Audit). This ticket will produce a risk report and determine if we are clear to proceed to Sequence #26.

## Governing documents

- tickets/AUD-006.md (READY)
- docs/handoff/IMPLEMENTATION_SEQUENCE.md

## Acceptance (Jr)

1. Audit report committed to `docs/reviews/`.
2. python3 scripts/check_repo_control.py
