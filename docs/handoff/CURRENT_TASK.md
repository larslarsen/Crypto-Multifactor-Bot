# CURRENT_TASK

Ticket: CEX-002
State: IN_PROGRESS
Next required actor: Sr Dev - Codex Sol using GPT-5.6-sol High
Final reviewer: Lead Quantitative Finance Researcher/Engineer
Next ticket authorized: NONE

Review 367 accepts record 366 as faithful blocked execution evidence and identifies a
repository-native reader/writer mismatch. Generation 0 legitimately stores `consumable`
on selected-manifest `daily/metrics` payloads and `etag` on cost-sample
`daily/bookTicker` payloads; the integrated planner and its synthetic helper omitted both.

Sol High is authorized for Review 367's exact two-path source/test correction and one
targeted synthetic pytest invocation. The correction must accept only the two exact
family-specific production shapes and keep missing, cross-family, additional, and
wrong-type fields fail-closed. It may not touch the CLI or fixtures.

CEX-002 remains `IN_PROGRESS`. Gate 2 remains `IN_PROGRESS`. Next ticket remains `NONE`.
All real planner retry/resume, repair, deletion, cleanup, acquisition, transition,
Hermes integration, lint, repository control, later-gate, and next-ticket work remains
unauthorized pending reviewer inspection of Sol's bounded result.

Governing documents:

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
