# CURRENT_TASK

Ticket: CEX-002
State: IN_PROGRESS
Final reviewer: Lead Quantitative Finance Researcher/Engineer
Next required actor: Lead Quantitative Finance Researcher/Engineer
Next ticket: NONE
Next ticket authorized: NONE

Review 405 accepts record 404's safe no-launch facts and exact three-path publication but rejects its mismatch diagnosis. Hermes compared Review 403's acquisition source/CLI hashes against two different qualification files. The five path-explicit v3/test/planner-CLI/acquisition-source/acquisition-CLI rows in Review 405 all match exactly; qualification paths are excluded. No planner, runner, network request, SQLite open, or v3 tree occurred, so no invocation was consumed. Record 404 also left the ticket actor field stale; Review 405 records and supersedes that defect. No candidate, acquisition, Gate-2 result, transition, or later ticket is accepted.

Review 407 accepts record 406's exact three-path publication and bounded safe preflight/one-launch/external-kill/no-publication facts, but rejects its checkpoint and runner-compliance claims. The checkpoint proves pass 1 is incomplete, not complete: 1,468 pages, 1,308 discovered prefixes, 953 completed prefixes, `listing_complete=false`, and a non-null continuation at `data/futures/um/daily/metrics/NTRNUSDT/`. Pass 2 is initialized but incomplete with zero pages. Hermes killed the live runner after ~34.7 minutes despite Review 405's four-hour allowance; the runner also omitted a planner PID/start ticks, used wall-clock nanoseconds instead of Linux shell start ticks, and captured no terminal trailer. Record 406 is rejected as an exact execution record. No candidate is accepted.

Review 408 (record 408) publishes the mandatory durable v3 continuation evidence under Review 407. Preflight passed: HEAD == origin/main == 2491226e260d711cedf1868f4a2b6ce9da07153e, staging empty, five literal code paths and immutable v1/v2 checkpoint/private-index hashes all match exactly. The runner /tmp/runner_407_KyKikU captured real shell PID 589947/start tick 6458981 and planner PID 589954/start tick 6458983 from /proc/<pid>/stat field 22. The planner reached natural terminal exit 2 after 966 seconds (16m06s) due to a transient listing request failure — NOT killed by process.kill or any signal. The runner wrote an atomic terminal trailer with EXIT_STATUS=2. Checkpoint: pass 1 partial at 2,001 pages, 1,308 discovered prefixes, 1,257 completed prefixes, listing_complete=false, cursor at data/futures/um/daily/metrics/XAGUSDT/. Pass 2: 0 pages, listing_complete=false. No locator/receipt/manifest/lineage was published. No duplicate invocation. No source/test edit, acquisition, transition, or next ticket. Untracked root file run_continuation_runner.sh is byte-identical to /tmp/runner_407_KyKikU/run.sh (SHA-256 d5c4a6b07531b52a95414b9d2a8178de11135e5f4f0b5b09e538ce20748ee820, 2922 bytes) and is an unstaged runner-evidence copy created during launch, not one of the 13 unrelated untracked paths. The prior handoff claim that a stale intermediate was removed is INCORRECT. No candidate is accepted. No acquisition or transition is authorized.

CEX-002 and Gate 2 remain `IN_PROGRESS`; next ticket remains `NONE`.

Governing documents:

- `research/sprint_004/407_CEX002_RECORD406_REJECTION_AND_DURABLE_V3_CONTINUATION_AUTHORIZATION.md`
- `research/sprint_004/406_CEX002_FRESH_V3_REVISION_CANDIDATE_RUN_RECORD.md`
- `research/sprint_004/405_CEX002_RECORD404_PREFLIGHT_DIAGNOSIS_CORRECTION_AND_V3_REAUTHORIZATION.md`
- `research/sprint_004/404_CEX002_FRESH_V3_REVISION_CANDIDATE_RUN_RECORD.md`
- `research/sprint_004/403_CEX002_RECORD402_ACCEPTANCE_AND_FRESH_V3_LISTING_AUTHORIZATION.md`
- `research/sprint_004/402_CEX002_V3_INTEGRATION_COMMAND_EVIDENCE_COMPLETION.md`
- `research/sprint_004/401_CEX002_RECORD400_INTEGRATION_ACCEPTANCE_AND_COMMAND_EVIDENCE_CORRECTION.md`
- `research/sprint_004/400_CEX002_V3_REACHABILITY_INTEGRATION_RECORD.md`
- `research/sprint_004/399_CEX002_SOL_V3_REACHABILITY_SOURCE_ACCEPTANCE_FOR_HERMES_INTEGRATION.md`
- `research/sprint_004/398_CEX002_SOL_V3_STOPPED_DROP_REJECTION_AND_CAPACITY_SEMANTIC_CORRECTION_AUTHORIZATION.md`
- `research/sprint_004/397_CEX002_RECORD396_ACCEPTANCE_AND_SOL_V3_REACHABILITY_AUTHORIZATION.md`
- `docs/adr/0033-aggregate-prefix-reachability-and-v3-candidate.md`
- `research/sprint_004/396_CEX002_V2_DRIFT_DIAGNOSIS_AND_PUBLICATION_EVIDENCE_COMPLETION.md`
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
