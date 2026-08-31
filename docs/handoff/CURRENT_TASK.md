# CURRENT_TASK

Ticket: CEX-002
State: IN_PROGRESS
Next required actor: Jr Dev - Hermes - review-352 interrupted-run recovery and one acquisition continuation
Final reviewer: Lead Quantitative Finance Researcher/Engineer
Next ticket authorized: NONE

Review 352 accepts Hermes's safe outage stop, corrects record 351's omitted closed run, and
proves the current unsealed tail is the exact ADR-0029 interrupted-run recovery state. Run 5
closed normally at `max_wall_seconds`, adding 238,964 completions and 2,430,507,042 bytes. The
outage then left exactly one unfinished run 6 with 235,359 attempts, 92,215 completions,
92,219 sidecars, and 1,459,224,114 listed bytes beyond the sealed head. Reviewer read-only
path/type/size/SHA-256 reconciliation found zero defects. No source or ADR change is required.

Hermes must follow Review 352's exact preproof and run one externally network-enabled standard
84,600-second acquisition invocation. Its binding phase must first finalize and seal run 6
under its original identity with stop reason `interrupted`; only then may run 7 continue the
frozen plan. Any recovery discrepancy or command result ends the one-invocation campaign.
Publish only record 353 and stop. Do not run a second acquisition, manual recovery, plan,
replay, `verify`, revision disposal, later gate, or next-ticket work. Next ticket is `NONE`.

Governing documents:

- `tickets/CEX-002.md`
- `research/sprint_004/352_CEX002_POWER_INTERRUPTION_RECOVERY_AND_CONTINUATION.md`
- `research/sprint_004/351_CEX002_BOUNDED_ACQUISITION_CONTINUATION.md`
- `research/sprint_004/350_CEX002_PREPROOF_FALSE_NEGATIVE_AND_CONTINUATION.md`
