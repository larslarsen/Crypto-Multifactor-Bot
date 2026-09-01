# CEX-002 Corrected Revision-Candidate Run Record

- **Date:** 2026-09-01
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** one authorized corrected listing-only candidate invocation executed; exit 1 blocked; no candidate tree published
- **Executing actor:** Jr Dev - Hermes through the installed Hermes one-shot harness
- **Gate 2:** `IN_PROGRESS`
- **Next ticket:** `NONE`

## Durable run disposition

Hermes executed exactly one authorized invocation of the corrected listing-only revision-candidate planner. The command exited status 1 with a blocked refusal and published no candidate tree. No raw ZIP GET, no Coinalyze secret access, no active-generation edit, no family/symbol/key/date subset selection, no cleanup, no replacement of an existing candidate, no old-acquisition invocation, and no generation transition occurred. This record is execution evidence, not acceptance; the repository record is authoritative.

## Run identification

- **Start UTC:** `2026-09-01T00:28:35Z`
- **End UTC:** `2026-09-01T00:28:49Z`
- **Command:** `PYTHONPATH=src .venv/bin/python scripts/research/plan_binance_usdm_gate2_revision_candidate.py`
- **Exit code:** **1**
- **Stop reason:** `blocked` — the planner refused because a retained sidecar path is not the canonical content-addressed leaf.
- **Stdout:** (empty)
- **Stderr:**
  ```
  command=plan_revision_candidate exit=1 stop=blocked
  ERROR: a retained sidecar path is not the canonical content-addressed leaf
  ```

## Pre-run authority proof

- **HEAD:** `c99a089cbf0162fbf26b4db39bfb63237de877f4`
- **origin/main:** `c99a089cbf0162fbf26b4db39bfb63237de877f4`
- **HEAD == origin/main:** true
- **Production path:** `src/cryptofactors/acquisition/binance_usdm_gate2_revision_candidate.py`
  - SHA-256: `06d43d085e3d38d8af9043ebc6a5353c8d7de8bf9bd9cde0ac6e3e94b9e6e553`
  - Lines: 5,095
- **CLI path:** `scripts/research/plan_binance_usdm_gate2_revision_candidate.py`
  - SHA-256: `9e203790432d412d489120fdef6bcb19831cf10461cecc38e7b1f23c41fb0d1a`
  - Lines: 87
- **Test path:** `tests/acquisition/test_binance_usdm_gate2_revision_candidate.py`
  - SHA-256: `e708e7ac9ddf183fd2702cfca97677a5dc761966819f9f1aedecb81106704630`
  - Lines: 2,593

All installed identities exactly match Review 370.

## Execution scope confirmation

- The command ran exactly once.
- No raw ZIP GET was performed.
- No acquisition command was executed.
- No Coinalyze secret was accessed.
- No active generation was edited.
- No family/symbol/key/date subset was selected.
- No existing candidate was cleaned or replaced.
- No generation transition was started.

## Candidate tree inspection

The planner exited before publishing any candidate tree. Read-only inspection confirms:

- **Locator path:** `data/cex002_qualify/gate2_revision_candidate`
- **Locator exists:** false
- **Published manifest:** none
- **Published receipt:** none
- **Published lineage assets:** none
- **Checkpoint/pages/tmp subdirectories:** none

No candidate checkpoint, page cache, temporary partial, manifest, receipt, or lineage file was created. No SHA-256 or byte identities are available because no candidate artifacts exist.

## Blocked-result record

- **Exact refusal:** `ERROR: a retained sidecar path is not the canonical content-addressed leaf`
- **Locator exists:** false
- **Interpretation:** The planner detected that a retained sidecar path is not the canonical content-addressed leaf and refused to construct a candidate. This is a fail-closed blocked outcome, not a partial or unsafe result. No candidate evidence was produced.

## Authorization boundaries

This candidate result does not accept a revision, does not authorize raw acquisition, does not authorize a generation transition, and does not pass Gate 2. The active generation-0 plan and its 51,275 unresolved identities remain pending. No further invocation, retry, resume, repair, deletion, cleanup, or patch is authorized by this run.

## Repository transition

After recording this evidence, Hermes updates `docs/handoff/CURRENT_TASK.md` and `tickets/CEX-002.md` to keep CEX-002 `IN_PROGRESS`, name the reviewer as the next required actor in both top-level actor fields, keep next ticket `NONE`, report this exact blocked run outcome, and state that all retry/resume/acquisition/transition/later work remains unauthorized. Hermes runs `python3 scripts/check_repo_control.py` only after those final top-level fields and this record exist, then runs a diff check scoped to this record and the two control-plane paths. Hermes stages exactly this record, `CURRENT_TASK.md`, and `tickets/CEX-002.md`; verifies no other path is staged; commits; pushes `main`; proves `HEAD == origin/main`; and stops. Candidate data is not staged or committed. Harness output is a handoff aid only; all execution evidence and state are repository-native.
