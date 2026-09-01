# CEX-002 Sidecar-Corrected Revision-Candidate Run Record

- **Date:** 2026-09-01
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** one authorized corrected listing-only candidate invocation executed; partial candidate tree published; pass_2 not started
- **Executing actor:** Jr Dev - Hermes through the installed Hermes one-shot harness
- **Gate 2:** `IN_PROGRESS`
- **Next ticket:** `NONE`

## Durable run disposition

Hermes executed exactly one authorized invocation of the corrected listing-only revision-candidate planner. The command was interrupted after the bounded timeout with exit code 124. A partial candidate tree was published: pass_1 completed with 640 pages and 1,308 discovered prefixes; pass_2 discovered its two root prefixes but published zero pages and made zero ListObjectsV2 requests beyond the root discovery. No raw ZIP GET, no Coinalyze secret access, no active-generation edit, no family/symbol/key/date subset selection, no cleanup, no replacement of an existing candidate, no old-acquisition invocation, and no generation transition occurred. This record is execution evidence, not acceptance; the repository record is authoritative.

## Run identification

- **Start UTC:** `2026-09-01T01:04:18Z`
- **End UTC:** `2026-09-01T01:26:12Z`
- **Command:** `PYTHONPATH=src .venv/bin/python scripts/research/plan_binance_usdm_gate2_revision_candidate.py`
- **Exit code:** **124**
- **Stop reason:** `interrupted` — the planner was terminated after the bounded timeout; pass_1 completed, pass_2 started but published no pages
- **Stdout:** (empty)
- **Stderr:** (empty)

## Pre-run authority proof

- **HEAD:** `e7ca17f1eaf0cb0801679474254cbb4eb6ae981e`
- **origin/main:** `e7ca17f1eaf0cb0801679474254cbb4eb6ae981e`
- **HEAD == origin/main:** true
- **Staging area:** empty at validation time
- **Production path:** `src/cryptofactors/acquisition/binance_usdm_gate2_revision_candidate.py`
  - SHA-256: `8cef6be834b9a61c6ffdda3b8e59fb72e8effa94aa2ea4bd2a83b12c10dee87b`
  - Lines: 5,096
- **CLI path:** `scripts/research/plan_binance_usdm_gate2_revision_candidate.py`
  - SHA-256: `9e203790432d412d489120fdef6bcb19831cf10461cecc38e7b1f23c41fb0d1a`
  - Lines: 87
- **Test path:** `tests/acquisition/test_binance_usdm_gate2_revision_candidate.py`
  - SHA-256: `aa4a09b4c8bee732515961c09ac890ef83f69be6395dd9c3770c4383ee05b149`
  - Lines: 2,646

All installed identities exactly match Review 373 and remain unchanged.

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

The planner published a partial candidate tree before interruption. Read-only inspection confirms:

- **Locator path:** `data/cex002_qualify/gate2_revision_candidate`
- **Locator exists:** true
- **Published manifest:** none (manifest directory empty)
- **Published receipt:** none (receipts directory empty)
- **Published lineage assets:** none (lineage directory empty)
- **Checkpoint:** `data/cex002_qualify/gate2_revision_candidate/checkpoint.json`
  - SHA-256: `de0527f99bbf24463d8bdc774e5cf51f356aeb14d7ee5b821d0e9384dc6152b3`
  - Bytes: 1,261,084
  - Lines: 22,705
- **Candidate lock:** `data/cex002_qualify/gate2_revision_candidate/candidate.lock` (0 bytes)
- **Pages directory:** 640 files under `pages/`
- **Temporary SQLite:** `data/cex002_qualify/gate2_revision_candidate/tmp/listing.sqlite`
  - SHA-256: `da438ce8b812e67647d02d0451e0187f185309d1f83b4646083f47b34d5a81d1`
  - Bytes: 163,332,096

## Partial-result record

### Checkpoint identity

- **Schema version:** `cex002_gate2_revision_candidate_checkpoint_v1`
- **S3 endpoint:** `https://s3-ap-northeast-1.amazonaws.com/data.binance.vision`
- **Family prefixes:** `data/futures/um/daily/metrics/`, `data/futures/um/daily/bookTicker/`
- **Pending identity SHA-256:** `6ac5daa6636092415ce0c01982f05acba4018f65aec85eec67a0db62fe882b61`
- **Generation plan identity:** `8d96db46d5b6df45e4b9c0ba0e45ae9f3688dd88503195fb426e12de827bde22`
- **Generation state SHA-256:** `5a5bdc8745c51b1b4b4a15e0de12b7dfa405f8c3a8ae1ba759aa0b6fd7ee33b4`

### Code identity (from checkpoint)

- **Acquisition CLI SHA-256:** `6f4b56ecb43dcc448eb6c8cf765e38d9fa3923432459574d913582e3d9c84043`
- **Acquisition source SHA-256:** `af6ef568b9f0f30827b393efc013b13560d4fd5761ec86417c0d2cf461e1248d`
- **Planner CLI SHA-256:** `9e203790432d412d489120fdef6bcb19831cf10461cecc38e7b1f23c41fb0d1a`
- **Planner source SHA-256:** `8cef6be834b9a61c6ffdda3b8e59fb72e8effa94aa2ea4bd2a83b12c10dee87b`

### Pass_1 (metrics prefix)

- **Completed prefixes:** 484
- **Published pages:** 640
- **Graph entries:** 640
- **Discovered prefixes:** 1,308
- **Seen tokens:** 92
- **Roots:** `3e148247d863e92ab1b3b06c45db7ada5653130dff091f12c9006825e68b445d`, `fe23d9b950114a21e8c72fe19031885c7cc08c83ffd6d986386b9e4231d79bd2`
- **Cursor:** `continuation_token=null`, `prefix=data/futures/um/daily/metrics/BNXUSDT/`
- **Listing complete:** false

### Pass_2 (bookTicker prefix)

- **Completed prefixes:** 0
- **Published pages:** 0
- **Graph entries:** 0
- **Discovered prefixes:** 2
- **Seen tokens:** 0
- **Roots:** `3e148247d863e92ab1b3b06c45db7ada5653130dff091f12c9006825e68b445d`, `fe23d9b950114a21e8c72fe19031885c7cc08c83ffd6d986386b9e4231d79bd2`
- **Cursor:** `continuation_token=null`, `prefix=data/futures/um/daily/bookTicker/`
- **Listing complete:** false

### Page identity sample (SHA-256 content-addressed)

- `705dcd9d887eaed67c2a474001d5d365491157bcde6431f995f7bd582d548b0d`
- `7089edc4117ba937e52eadca83e8d45b5c8052aa923157c7509f47890c26a367`
- `fb90e030c717e6dac187edb6f66038b344e44f5d76b1162b3a8c9364eaa7c68a`
- `fb7b9533314f244d2849ab31c96d2b5b5423a655646785261ecfc6e3b14f0b4c`
- `de8c9ce13de6c610ce44b5149e79a1fc559e29b6413a9bbbd409cb756d5f27f9`

## Authorization boundaries

This candidate result does not accept a revision, does not authorize raw acquisition, does not authorize a generation transition, and does not pass Gate 2. The active generation-0 plan and its 51,275 unresolved identities remain pending. No further invocation, retry, resume, repair, deletion, cleanup, or patch is authorized by this run.

## Repository transition

After recording this evidence, Hermes updates `docs/handoff/CURRENT_TASK.md` and `tickets/CEX-002.md` to keep CEX-002 `IN_PROGRESS`, name the reviewer as the next required actor in both top-level actor fields, keep next ticket `NONE`, report this exact partial run outcome, and state that all retry/resume/acquisition/transition/later work remains unauthorized. Hermes runs `python3 scripts/check_repo_control.py` only after those final top-level fields and this record exist, then runs a diff check scoped to this record and the two control-plane paths. Hermes stages exactly this record, `CURRENT_TASK.md`, and `tickets/CEX-002.md`; verifies no other path is staged; commits; pushes `main`; proves `HEAD == origin/main`; and stops. Candidate data is not staged or committed. Harness output is a handoff aid only; all execution evidence and state are repository-native.
