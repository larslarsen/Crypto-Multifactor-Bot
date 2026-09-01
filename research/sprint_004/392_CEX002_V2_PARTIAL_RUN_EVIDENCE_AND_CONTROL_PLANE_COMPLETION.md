# CEX-002 V2 Partial-Run Evidence and Control-Plane Completion

- **Date:** 2026-09-01
- **Actor:** Jr Dev - Hermes
- **Ticket:** CEX-002
- **Review:** 391
- **Gate 2:** `IN_PROGRESS`
- **Next ticket:** `NONE`

## Evidence actor

Jr Dev - Hermes is the evidence and publication actor. No planner, resume, network, data or candidate mutation, SQLite query, source/test edit, cleanup, acquisition, transition, or later work occurred during this correction.

## Record 390 preserved

Record 390 is preserved unchanged. This record does not rewrite, replace, or modify record 390.

## Accepted Review-391 run facts

From the one Review-389 planner invocation, the reviewer accepts these independently reverified facts:

- the exact planner command started at `2026-09-01T05:19:29Z` under shell PID `462949` and terminated at `2026-09-01T06:01:19Z`, 41 minutes 50 seconds later;
- durable `status.txt` reports `SHELL_PID=462949 EXIT_CODE=2`;
- durable stderr reports `exit=2 stop=resumable_partial` and `ERROR: listing request failed transiently`; stdout is empty;
- the v2 checkpoint SHA-256 is `aaaaf68a0f0f132d086140f66f6526905f70eaf5c2cc31c35c51431e3ffc6748`, size 3,478,715 bytes, schema `cex002_gate2_revision_candidate_checkpoint_v2`, and pending identity `6ac5daa6636092415ce0c01982f05acba4018f65aec85eec67a0db62fe882b61`;
- pass 1 is incomplete at 1,164 completed of 1,308 discovered prefixes, 1,838 published graph pages, and the null-token cursor for `data/futures/um/daily/metrics/TAUSDT/`;
- pass 2 remains incomplete at zero completed of two initialized roots and zero pages;
- exactly 1,838 retained v2 page files exist, while manifest, receipt, lineage, and locator publication is absent;
- v1 checkpoint SHA-256 remains `2a9ed07c2adb72e9311e64fe93b10edd818558f521f0fabef73567f0a51d86a0` and v1 private-index SHA-256 remains `fb27538b340015ebdbe3c9737e9f70d1ec66b0a826464d145fecf7484fd0ccfc`; and
- no planner process is now live, `HEAD == origin/main == 7d585f9b04df5c3538f7d74f7142a403acc3585f`, and staging is empty.

This is an ordinary resumable partial listing outcome, not candidate acceptance or a source defect. No raw acquisition, candidate acceptance, Gate-2 acceptance, transition, or later work is authorized by the result.

## Runner lacks Linux start ticks

Review 389 required durable Linux start ticks. The runner has no start-tick file. Record 390's Python PID `463025` is therefore not durably process-identity-bound. The runner does not durably prove the Python PID.

## Exact seven runner file identities

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `start_utc.txt` | 21 | `63962bef3d33cbb9258cdb18fd2e1dd16ad75ee76daf609cb67bdaee2259eac1` |
| `end_utc.txt` | 21 | `0f65b7df3511de353b98fbae228ba5ca0973445731db1e4d6e6ae23bf2e34556` |
| `shell_pid.txt` | 7 | `7213ea4d71a16937eb70b615f81f09950ad171fe57ba4af098ab69fd47903db4` |
| `exit_code.txt` | 2 | `53c234e5e472b6ac51c1ae1cab3fe06fad053beb8ebfd8977b010655bfdd3c3` |
| `status.txt` | 29 | `6cd106b1e6a277b0965b203a7208e3694779301dc0910f2e9990ded0515be119` |
| `stdout.txt` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `stderr.txt` | 213 | `9bfdb8d16d4ea9a0b7b68c7272a6fbdbb887e6447ecb8248b234d008d9d3f18a` |

## One-path commit defect and stale summaries

Commit `0ddb59f5ced7784aec97dc7cb740c9a8870c2562` contains only record 390. `CURRENT_TASK.md` and `tickets/CEX-002.md` retained the completed fresh invocation as future work and named Hermes as the next required actor. Both summaries remained stale.

## Fresh publication-check evidence

### Command 1

```text
python3 scripts/check_repo_control.py
```

- stdout: `Repo control check: PASS`
- stderr: empty
- exit code: `0`

### Command 2

```text
git diff --check -- docs/handoff/CURRENT_TASK.md research/sprint_004/392_CEX002_V2_PARTIAL_RUN_EVIDENCE_AND_CONTROL_PLANE_COMPLETION.md tickets/CEX-002.md
```

- stdout: empty
- stderr: empty
- exit code: `0`

## Outcome statement

This record publishes the exact Review-391 partial-run facts, the missing start-tick/Python-PID limitation, all seven runner identities, the one-path commit defect, and the exact fresh publication-check evidence. It does not accept a v2 candidate, does not authorize raw acquisition, and does not authorize a generation transition. CEX-002 and Gate 2 remain `IN_PROGRESS`. The next ticket remains `NONE`. No retry, resume, repair, cleanup, or second invocation is authorized.

## Final actor fields

- **Next required actor:** Lead Quantitative Finance Researcher/Engineer
