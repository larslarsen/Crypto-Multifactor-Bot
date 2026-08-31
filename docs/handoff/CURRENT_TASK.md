# CURRENT_TASK

Ticket: CEX-002
State: IN_PROGRESS
Next required actor: Jr Dev - Hermes - integrate exact review-363 corrected drop
Final reviewer: Lead Quantitative Finance Researcher/Engineer
Next ticket authorized: NONE

Review 363 accepts Sol High's exact Review-362 prerequisite assertion and corrected test SHA-256
`065e6a...795c1` for bounded Hermes integration. Production, CLI, and fixture identities remain
unchanged from Review 361. The correction consumes the ruff-reported variable by asserting the
initial candidate completed before receipt forgery; Sol made no other byte change or command.

Hermes must rehash/stage only the six Review-363 identities, rerun the exact targeted pytest,
ruff, repository-control, and scoped diff commands, publish durable record 364 and control-plane
updates, commit, push, prove `HEAD == origin/main`, and stop. It must patch nothing and preserve
all unrelated dirty paths. Harness output is not a decision surface. Real planner/network/data/
acquisition/generation-transition work remains unauthorized. Gate 2 stays `IN_PROGRESS`; next
ticket is `NONE`.

Governing documents:

- `tickets/CEX-002.md`
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
