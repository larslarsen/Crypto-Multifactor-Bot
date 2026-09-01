# CURRENT_TASK

Ticket: CEX-002
State: IN_PROGRESS
Next required actor: Jr Dev - Hermes through the installed Hermes one-shot harness
Final reviewer: Lead Quantitative Finance Researcher/Engineer
Next ticket authorized: NONE

Review 368 accepts Sol High's exact two-path payload-schema correction for Hermes
integration. The planner now requires the writer-authoritative `consumable` field on
`daily/metrics` and `etag` on `daily/bookTicker`, with exact family-specific shapes and
types. Missing, cross-family, additional, and wrong-type fields remain fail-closed.
Sol's one authorized targeted run exited zero with all 119 cases passing.

Hermes is authorized only to integrate the two accepted hashes, execute Review 368's
four-command validation chain, publish durable record 369 and matching control-plane
updates, commit/push exactly five paths, prove `HEAD == origin/main`, and stop.

CEX-002 remains `IN_PROGRESS`. Gate 2 remains `IN_PROGRESS`. Next ticket remains `NONE`.
All real planner retry/resume, listing, real-state/data access, repair, deletion, cleanup,
acquisition, transition, later-gate, and next-ticket work remains unauthorized pending
reviewer inspection of Hermes's bounded integration.

Governing documents:

- `research/sprint_004/368_CEX002_PAYLOAD_SCHEMA_SOURCE_ACCEPTANCE_FOR_HERMES_INTEGRATION.md`
- `research/sprint_004/367_CEX002_BLOCKED_CANDIDATE_PAYLOAD_SCHEMA_CORRECTION_AUTHORIZATION.md`
- `tickets/CEX-002.md`
- `research/sprint_004/366_CEX002_REVISION_CANDIDATE_RUN_RECORD.md`
- `research/sprint_004/365_CEX002_REVISION_CANDIDATE_INTEGRATION_ACCEPTANCE_AND_RUN_AUTHORIZATION.md`
- `research/sprint_004/364_CEX002_REVISION_CANDIDATE_INTEGRATION_RECORD.md`
- `research/sprint_004/363_CEX002_CORRECTED_REVISION_CANDIDATE_INTEGRATION_REAUTHORIZATION.md`
- `research/sprint_004/362_CEX002_HERMES_INTEGRATION_VALIDATION_STOP.md`
- `research/sprint_004/361_CEX002_SOL_REVISION_CANDIDATE_SOURCE_ACCEPTANCE_FOR_HERMES_INTEGRATION.md`
- `research/sprint_004/360_CEX002_SOL_RECOVERY_CORRECTION_WARNING_STATIC_REJECTION.md`
- `research/sprint_004/359_CEX002_SOL_CORRECTED_REVISION_CANDIDATE_RECOVERY_STATIC_REJECTION.md`
- `research/sprint_004/358_CEX002_SOL_REVISION_CANDIDATE_SOURCE_STATIC_REJECTION.md`
- `research/sprint_004/357_CEX002_SOL_HIGH_REVISION_CANDIDATE_REROUTE.md`
- `research/sprint_004/356_CEX002_GROK_SECOND_REVISION_CANDIDATE_SOURCE_STATIC_REJECTION.md`
- `research/sprint_004/355_CEX002_GROK_REVISION_CANDIDATE_SOURCE_STATIC_REJECTION.md`
- `docs/adr/0031-post-plan-revision-authority-and-bounded-zip-validation.md`
- `research/sprint_004/354_CEX002_GATE2_END_OF_PLAN_REVIEW_AND_REVISION_ARCHITECTURE.md`
- `research/sprint_004/353_CEX002_INTERRUPTED_RECOVERY_AND_ACQUISITION_CONTINUATION.md`
