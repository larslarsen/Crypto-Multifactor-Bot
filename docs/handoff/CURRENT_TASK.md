# CURRENT_TASK

Ticket: CEX-002
State: IN_PROGRESS
Final reviewer: Lead Quantitative Finance Researcher/Engineer
Next required actor: Jr Dev - Hermes
Next ticket: NONE
Next ticket authorized: NONE

Review 395 accepts the exact Review-393 terminal/run facts but rejects record 394's diagnosis. Both
passes are complete with null cursors. The first normalized difference is `BANKUSDT`: pass 1 ended
in one non-truncated page through 2026-08-30; pass 2 observed the newly published 2026-08-31 ZIP
and checksum, crossed the 1,000-object boundary, and required a second page. ADR-0032 correctly
blocked real live-listing growth. No manifest, receipt, lineage, locator, candidate, or Gate-2
result is accepted.

Record 394 also omits both required publication-command results and incorrectly denies the one
authorized planner resume. Hermes is authorized only to publish record 396 with the corrected
diagnosis and fresh repository-control/scoped-diff evidence, update both final reviewer actor
fields and summaries, commit/push exactly three paths, and stop. No planner, retry/resume, network,
data/candidate/runner mutation, SQLite, source/architecture change, acquisition, cleanup,
transition, or later work is authorized. CEX-002 and Gate 2 remain `IN_PROGRESS`; next ticket
remains `NONE`.

Governing documents:

- `research/sprint_004/395_CEX002_RECORD394_DIAGNOSIS_CORRECTION_AND_EVIDENCE_STOP.md`
- `research/sprint_004/394_CEX002_V2_REVISION_CANDIDATE_CONTINUATION_RECORD.md`
- `research/sprint_004/393_CEX002_RECORD392_ACCEPTANCE_AND_V2_CONTINUATION_AUTHORIZATION.md`
- `research/sprint_004/392_CEX002_V2_PARTIAL_RUN_EVIDENCE_AND_CONTROL_PLANE_COMPLETION.md`
- `research/sprint_004/391_CEX002_RECORD390_PARTIAL_RUN_ACCEPTANCE_AND_CONTROL_PLANE_EVIDENCE_STOP.md`
- `research/sprint_004/390_CEX002_FRESH_V2_REVISION_CANDIDATE_RUN_RECORD.md`
- `research/sprint_004/389_CEX002_V2_CURSOR_CORRECTION_INTEGRATION_ACCEPTANCE_AND_FRESH_RUN_AUTHORIZATION.md`
- `research/sprint_004/388_CEX002_V2_CURSOR_CORRECTION_INTEGRATION_RECORD.md`
- `research/sprint_004/387_CEX002_SOL_V2_CURSOR_CORRECTION_SOURCE_ACCEPTANCE_FOR_HERMES_INTEGRATION.md`
- `research/sprint_004/386_CEX002_RECORD385_ACCEPTANCE_AND_SOL_V2_CURSOR_CORRECTION_AUTHORIZATION.md`
- `docs/adr/0032-opaque-listing-cursor-normalization-and-v2-candidate.md`
- `research/sprint_004/385_CEX002_DUPLICATE_INVOCATION_AND_DRIFT_BLOCKER_RECORD.md`
- `research/sprint_004/384_CEX002_HERMES_DUPLICATE_INVOCATION_CONTROL_STOP.md`
- `research/sprint_004/383_CEX002_RECORD382_HASH_REJECTION_AND_OFFLINE_CAPTURE_RETRY_AUTHORIZATION.md`
- `research/sprint_004/382_CEX002_REVISION_CANDIDATE_RESUME_RECORD.md`
- `research/sprint_004/381_CEX002_PARTIAL_CHECKPOINT_CORRECTION_AND_RESUME_AUTHORIZATION.md`
- `research/sprint_004/379_CEX002_SIDECAR_PATH_INTEGRATION_ACCEPTANCE_AND_REAL_RETRY_AUTHORIZATION.md`
- `research/sprint_004/378_CEX002_INTEGRATION_EVIDENCE_ATTRIBUTION_AND_CONTROL_PLANE_CORRECTION.md`
- `research/sprint_004/377_CEX002_INTEGRATION_EVIDENCE_ATTRIBUTION_AND_CONTROL_PLANE_STOP.md`
- `research/sprint_004/376_CEX002_SIDECAR_PATH_INTEGRATION_EVIDENCE_COMPLETION.md`
- `research/sprint_004/375_CEX002_SIDECAR_PATH_INTEGRATION_EVIDENCE_STOP.md`
- `research/sprint_004/374_CEX002_SIDECAR_PATH_INTEGRATION_RECORD.md`
- `research/sprint_004/373_CEX002_SIDECAR_PATH_SOURCE_ACCEPTANCE_FOR_HERMES_INTEGRATION.md`
- `research/sprint_004/372_CEX002_BLOCKED_SIDECAR_PATH_SERIALIZATION_CORRECTION_AUTHORIZATION.md`
- `research/sprint_004/371_CEX002_CORRECTED_REVISION_CANDIDATE_RUN_RECORD.md`
- `research/sprint_004/370_CEX002_PAYLOAD_SCHEMA_INTEGRATION_ACCEPTANCE_AND_REAL_RETRY_AUTHORIZATION.md`
- `research/sprint_004/369_CEX002_PAYLOAD_SCHEMA_INTEGRATION_RECORD.md`
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
