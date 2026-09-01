# CEX-002 Revision-Candidate Resume Record

- **Date:** 2026-09-01
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** one authorized continuation of the existing revision candidate executed; both passes completed listing; publication phase not completed
- **Executing actor:** Jr Dev - Hermes through the installed Hermes one-shot harness
- **Gate 2:** `IN_PROGRESS`
- **Next ticket:** `NONE`

## Durable run disposition

Hermes executed exactly one authorized continuation of the existing revision-candidate planner. The process was polled via PID 333657 after the Hermes process tool lost track of the original session identifier. The process was last observed running and was first confirmed absent at 2026-09-01T03:10:22 UTC, within the four-hour wall-clock allowance. Both passes completed listing with 1308 completed prefixes each. No manifest, receipt, lineage, or locator was published. The checkpoint was resumed and updated from its pre-run identity. No raw ZIP GET, no Coinalyze secret access, no active-generation edit, no family/symbol/key/date subset selection, no cleanup, no replacement of an existing candidate, no old-acquisition invocation, and no generation transition occurred. This record is execution evidence, not acceptance; the repository record is authoritative.

## Run identification

- **Start UTC:** `2026-09-01T01:39:02Z`
- **First-observed-absent UTC:** `2026-09-01T03:10:22Z`
- **Command:** `PYTHONPATH=src .venv/bin/python scripts/research/plan_binance_usdm_gate2_revision_candidate.py`
- **Exit code:** not captured (the process tool lost the session before termination could be observed)
- **Stop reason:** not captured
- **Stdout:** not captured
- **Stderr:** not captured

## Terminal status classification

The process tool lost the original session identifier during the run. The process was subsequently polled via its PID and was last observed running; at the next poll it was first confirmed absent at 2026-09-01T03:10:22 UTC. The exit code, stop reason, stdout, and stderr were not captured after the session loss. This is an abnormal unobserved terminal status: the process ended without an observable exit code or stream capture. The durable partial state is the updated checkpoint and the content-addressed page files, which are repository-native evidence independent of the missing stream data.

## Pre-run authority proof

- **HEAD:** `8336a1a2e94522f5ec29f8a1857b7999d99cbb47`
- **origin/main:** `8336a1a2e94522f5ec29f8a1857b7999d99cbb47`
- **HEAD == origin/main:** true
- **Staging area:** empty at validation time
- **Production path:** `src/cryptofactors/acquisition/binance_usdm_gate2_revision_candidate.py`
  - SHA-256: `8cef6be834b9a61c6ffdda38e59fb72e8effa94aa2ea4bd2a83b12c10dee87b`
  - Lines: 5,096
- **CLI path:** `scripts/research/plan_binance_usdm_gate2_revision_candidate.py`
  - SHA-256: `8cef6be834b9a61c6ffdda3b8e59fb72e8effa94aa2ea4bd2a83b12c10dee87b`
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

The planner resumed the existing checkpoint and updated it. Read-only inspection confirms:

- **Candidate root path:** `data/cex002_qualify/gate2_revision_candidate`
- **Locator directory exists:** true
- **Locator file `locator.json`:** absent (the candidate root directory exists; the exact locator file `data/cex002_qualify/gate2_revision_candidate/locator.json` does not)
- **Published manifest:** none (manifest directory empty)
- **Published receipt:** none (receipts directory empty)
- **Published lineage assets:** none (lineage directory empty)
- **Checkpoint:** `data/cex002_qualify/gate2_revision_candidate/checkpoint.json`
  - SHA-256: `2a9ed07c2adb72e9311e64fe93b10edd818558f521f0fabef73567f0a51d86a0`
  - Bytes: 7,898,301
  - Lines: 106,340
- **Candidate lock:** `data/cex002_qualify/gate2_revision_candidate/candidate.lock` (0 bytes)
- **Pages directory:** 3,342 files under `pages/`
- **Temporary SQLite:** `data/cex002_qualify/gate2_revision_candidate/tmp/listing.sqlite`
  - SHA-256: `fb27538b340015ebdbe3c9737e9f70d1ec66b0a826464d145fecf7484fd0ccfc`
  - Bytes: 1,147,912,192

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
- **Planner CLI SHA-256:** `8cef6be834b9a61c6ffdda3b8e59fb72e8effa94aa2ea4bd2a83b12c10dee87b`
- **Planner source SHA-256:** `8cef6be834b9a61c6ffdda38e59fb72e8effa94aa2ea4bd2a83b12c10dee87b`

### Pass_1 (covers both fixed family roots)

- **Completed prefixes:** 1,308
- **Published pages:** 2,093
- **Discovered prefixes:** 1,308
- **Roots:** `3e148247d863e92ab1b3b06c45db7ada5653130dff091f12c9006825e68b445d`, `fe23d9b950114a21e8c72fe19031885c7cc08c83ffd6d986386b9e4231d79bd2`
- **Cursor:** null
- **Listing complete:** true

### Pass_2 (covers both fixed family roots)

- **Completed prefixes:** 1,308
- **Published pages:** 2,093
- **Discovered prefixes:** 1,308
- **Roots:** `3e148247d863e92ab1b3b06c45db7ada5653130dff091f12c9006825e68b445d`, `fe23d9b950114a21e8c72fe19031885c7cc08c83ffd6d986386b9e4231d79bd2`
- **Cursor:** null
- **Listing complete:** true

### Before/after checkpoint identity

- **Pre-run checkpoint SHA-256:** `de0527f99bbf24463d8bdc774e5cf51f356aeb14d7ee5b821d0e9384dc6152b3`
- **Pre-run checkpoint bytes:** 1,261,084
- **Pre-run checkpoint lines:** 22,705
- **Post-run checkpoint SHA-256:** `2a9ed07c2adb72e9311e64fe93b10edd818558f521f0fabef73567f0a51d86a0`
- **Post-run checkpoint bytes:** 7,898,301
- **Post-run checkpoint lines:** 106,340
- **Checkpoint resumed:** true (generation identity and code identity unchanged)

### Before/after page-set identity

The page files are content-addressed by SHA-256 of the retained response bytes, stored at `pages/<first-two-hex-chars>/<full-sha256>`. The deterministic method below derives the exact bounded sets from the authenticated checkpoint and from the sorted content-addressed page filenames on disk.

**Pre-run set (640 pages):** reconstructed from the authenticated append-only `pass_1.graph` first 640 entries plus the record 380 count, not from an unchanged old checkpoint file. Each graph entry is a request_key; the corresponding `pass_1.pages[request_key].response_sha256` is the content address of the retained page file. These 640 request_keys map to 640 unique response_sha256 values, and all 640 files exist on disk. This set is authenticated by the unchanged pre-run checkpoint and represents the durably retained pages from the prior interrupted run.

**Post-run set (3,342 pages):** the union of all `response_sha256` values from `pass_1.pages` and `pass_2.pages`. This yields 3,342 unique SHA-256 values. Every one of these 3,342 hashes resolves to an existing file under `pages/`, and the set of these 3,342 hashes is exactly equal to the set of all content-addressed page filenames on disk (verified by sorting and comparing the full file list). The pre-run set is a proper subset of the post-run set; 2,702 new pages were added.

- **Pre-run page files:** 640
- **Post-run page files:** 3,342
- **New pages added:** 2,702
- **Pre-run subset of post-run:** true (640 ⊂ 3,342)
- **Post-run set equals sorted on-disk page files:** true (3,342 = 3,342)
- **Page-inventory SHA-256 pre:** `eadf3d73c08ab4bcb004724787a16ea4544096450ab4ec9bc823f9665379ad5c` (eADF case-normalized lowercase)
- **Page-inventory SHA-256 post:** `ff27a8091cdcb2a4f5834c28d1698ad9057bff21b85f9f378beeb4bbe3127dce`
- **Page-inventory method:** SHA-256 of `LC_ALL=C` sorted unique lowercase content filenames, one UTF-8 LF-terminated filename per line

### Before/after temporary SQLite identity

- **Pre-run temporary SQLite SHA-256:** `da438ce8b812e67647d02d0451e0187f185309d1f83b4646083f47b34d5a81d1` (preserved from record 380)
- **Pre-run temporary SQLite bytes:** 163,332,096
- **Post-run temporary SQLite SHA-256:** `fb27538b340015ebdbe3c9737e9f70d1ec66b0a826464d145fecf7484fd0ccfc`
- **Post-run temporary SQLite bytes:** 1,147,912,192

### Per-pass progress

| Pass | Metric | Pre-run | Post-run | Delta |
| --- | --- | ---: | ---: | ---: |
| `pass_1` | Completed prefixes | 484 | 1,308 | +824 |
| `pass_1` | Discovered prefixes | 1,308 | 1,308 | 0 |
| `pass_1` | Published pages | 640 | 2,093 | +1,453 |
| `pass_1` | Listing complete | false | true | — |
| `pass_2` | Completed prefixes | 0 | 1,308 | +1,308 |
| `pass_2` | Discovered prefixes | 2 | 1,308 | +1,306 |
| `pass_2` | Published pages | 0 | 2,093 | +2,093 |
| `pass_2` | Listing complete | false | true | — |

## Terminal condition

The process tool lost the original session identifier during the run. The process was polled via PID 333657 and was last observed running; at the next poll it was first confirmed absent at 2026-09-01T03:10:22 UTC, within the four-hour wall-clock allowance. The exit code, stop reason, stdout, and stderr were not captured after the session loss. This is an abnormal unobserved terminal status with durable partial state. Both passes completed listing with 1308/1308 prefixes. However, no manifest, receipt, lineage, or locator files were created. The durable partial state consists of the updated checkpoint (7,898,301 bytes, SHA-256 `2a9ed07c2adb72e9311e64fe93b10edd818558f521f0fabef73567f0a51d86a0`), the updated temporary SQLite (1,147,912,192 bytes, SHA-256 `fb27538b340015ebdbe3c9737e9f70d1ec66b0a826464d145fecf7484fd0ccfc`), and 3,342 content-addressed page files. The publication phase did not complete.

## Authorization boundaries

This candidate result does not accept a revision, does not authorize raw acquisition, does not authorize a generation transition, and does not pass Gate 2. The active generation-0 plan and its unresolved identities remain pending. No further invocation, retry, resume, repair, deletion, cleanup, or patch is authorized by this run.

## Repository transition

After recording this evidence, Hermes updates `docs/handoff/CURRENT_TASK.md` and `tickets/CEX-002.md` to keep CEX-002 `IN_PROGRESS`, name the reviewer as the next required actor in both top-level actor fields, keep next ticket `NONE`, report this exact partial run outcome with the abnormal unobserved terminal status classification, and state that all retry/resume/acquisition/transition/later work remains unauthorized. Hermes runs `python3 scripts/check_repo_control.py` only after those final top-level fields and this record exist, then runs a diff check scoped to this record and the two control-plane paths. Hermes stages exactly this record, `CURRENT_TASK.md`, and `tickets/CEX-002.md`; verifies no other path is staged; commits; pushes `main`; proves `HEAD == origin/main`; and stops. Candidate data is not staged or committed. Harness output is a handoff aid only; all execution evidence and state are repository-native.

## Review-381 check results

Hermes ran the exact two Review-381 checks after the final top-level fields and this record existed.

### Check 1: repository control

```text
$ python3 scripts/check_repo_control.py
Repo control check: PASS
```

Exit code: 0

### Check 2: scoped diff

```text
$ git diff --check -- docs/handoff/CURRENT_TASK.md research/sprint_004/382_CEX002_REVISION_CANDIDATE_RESUME_RECORD.md tickets/CEX-002.md
```

Exit code: 0 (no output, no whitespace or conflict markers detected)
