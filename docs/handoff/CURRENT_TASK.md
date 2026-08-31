# CURRENT_TASK

Ticket: CEX-002
State: IN_PROGRESS
Next required actor: Sr Dev - Codex Sol - review-360 manifest-iterator lifecycle correction
Final reviewer: Lead Quantitative Finance Researcher/Engineer
Next ticket authorized: NONE

Review 360 rejects the Review-359 correction before integration despite 109 passing cases. The
completed-recovery named-tree reauthentication and manifest stream ceilings are materially
correct and preserved. Three creation-ceiling cases emit `PytestUnraisableExceptionWarning`
because an early manifest refusal leaves the pending-row generator alive until after its SQLite
connection closes; delayed cursor cleanup then raises `sqlite3.ProgrammingError`.

Codex Sol High remains the sole senior actor for a lifecycle-only source/test correction. It must
explicitly close owned manifest iterators on all paths while SQLite is live and may run exactly
one new enumerated targeted pytest command. The result must be zero with no warning output. No
network/data action, real-state access, standalone planner, integration, records, or Git is
authorized. Hermes and all further acquisition remain unauthorized. Next ticket is `NONE`.

Governing documents:

- `tickets/CEX-002.md`
- `research/sprint_004/360_CEX002_SOL_RECOVERY_CORRECTION_WARNING_STATIC_REJECTION.md`
- `research/sprint_004/359_CEX002_SOL_CORRECTED_REVISION_CANDIDATE_RECOVERY_STATIC_REJECTION.md`
- `research/sprint_004/358_CEX002_SOL_REVISION_CANDIDATE_SOURCE_STATIC_REJECTION.md`
- `research/sprint_004/357_CEX002_SOL_HIGH_REVISION_CANDIDATE_REROUTE.md`
- `research/sprint_004/356_CEX002_GROK_SECOND_REVISION_CANDIDATE_SOURCE_STATIC_REJECTION.md`
- `research/sprint_004/355_CEX002_GROK_REVISION_CANDIDATE_SOURCE_STATIC_REJECTION.md`
- `docs/adr/0031-post-plan-revision-authority-and-bounded-zip-validation.md`
- `research/sprint_004/354_CEX002_GATE2_END_OF_PLAN_REVIEW_AND_REVISION_ARCHITECTURE.md`
- `research/sprint_004/353_CEX002_INTERRUPTED_RECOVERY_AND_ACQUISITION_CONTINUATION.md`
