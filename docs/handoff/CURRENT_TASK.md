# CURRENT_TASK

Ticket: CEX-002
State: IN_PROGRESS
Final reviewer: Lead Quantitative Finance Researcher/Engineer
Next required actor: Lead Quantitative Finance Researcher/Engineer
Next ticket: NONE
Next ticket authorized: NONE

Review 384 rejects Review-383 execution because Hermes launched the offline planner twice after
authorization for exactly one invocation. The first captured run exited 1 with
`listing reachability or pagination authority drifted across independent passes`; the second
launch overwrote part of the shared runner evidence. Both wrapper identities and every planner
process are now absent. The candidate checkpoint, private index, complete-pass graph, and physical
page-set identities remain unchanged; no manifest, receipt, lineage, or locator exists.

Read-only diagnosis finds the first pass difference at graph index 319: identical request key,
prefix, child-prefix facts, and truncation flag, but different opaque provider continuation-token
bytes. The source incorrectly requires those cursors to be equal across independent passes. No
source correction or further run is authorized yet.

Hermes is authorized only to publish record 385 and the two final reviewer summaries with exact
first-run, duplicate-launch, runner-overwrite, no-live-process, unchanged-candidate, corrected-code,
and graph-difference evidence. It may run only repository control and the scoped diff, then
commit/push exactly those three paths and stop. No planner, data/runner mutation, network, test,
source edit, acquisition, cleanup, transition, or later work is authorized. CEX-002 and Gate 2
remain `IN_PROGRESS`; next ticket remains `NONE`.

Governing documents:

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
