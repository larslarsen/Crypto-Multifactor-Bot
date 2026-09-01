# CEX-002 Record-390 Partial-Run Acceptance and Control-Plane Evidence Stop

- **Date:** 2026-09-01
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** accept exact partial-run facts; reject incomplete runner/publication claims; authorize evidence-only completion
- **Evidence actor:** Jr Dev - Hermes through the installed Hermes one-shot harness
- **Gate 2:** `IN_PROGRESS`
- **Next ticket:** `NONE`

## Accepted run facts

The reviewer accepts commit `0ddb59f5ced7784aec97dc7cb740c9a8870c2562` as publication of record
390 and accepts these independently reverified facts from the one Review-389 planner invocation:

- the exact planner command started at `2026-09-01T05:19:29Z` under shell PID `462949` and
  terminated at `2026-09-01T06:01:19Z`, 41 minutes 50 seconds later;
- durable `status.txt` reports `SHELL_PID=462949 EXIT_CODE=2`;
- durable stderr reports `exit=2 stop=resumable_partial` and
  `ERROR: listing request failed transiently`; stdout is empty;
- the v2 checkpoint SHA-256 is
  `aaaaf68a0f0f132d086140f66f6526905f70eaf5c2cc31c35c51431e3ffc6748`, size
  3,478,715 bytes, schema `cex002_gate2_revision_candidate_checkpoint_v2`, and pending identity
  `6ac5daa6636092415ce0c01982f05acba4018f65aec85eec67a0db62fe882b61`;
- pass 1 is incomplete at 1,164 completed of 1,308 discovered prefixes, 1,838 published graph
  pages, and the null-token cursor for `data/futures/um/daily/metrics/TAUSDT/`;
- pass 2 remains incomplete at zero completed of two initialized roots and zero pages;
- exactly 1,838 retained v2 page files exist, while manifest, receipt, lineage, and locator
  publication is absent;
- v1 checkpoint SHA-256 remains
  `2a9ed07c2adb72e9311e64fe93b10edd818558f521f0fabef73567f0a51d86a0` and v1
  private-index SHA-256 remains
  `fb27538b340015ebdbe3c9737e9f70d1ec66b0a826464d145fecf7484fd0ccfc`; and
- no planner process is now live, `HEAD == origin/main == 0ddb59f5ced7784aec97dc7cb740c9a8870c2562`,
  and staging is empty.

The accepted runner file identities are:

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `start_utc.txt` | 21 | `63962bef3d33cbb9258cdb18fd2e1dd16ad75ee76daf609cb67bdaee2259eac1` |
| `end_utc.txt` | 21 | `0f65b7df3511de353b98fbae228ba5ca0973445731db1e4d6e6ae23bf2e34556` |
| `shell_pid.txt` | 7 | `7213ea4d71a16937eb70b615f81f09950ad171fe57ba4af098ab69fd47903db4` |
| `exit_code.txt` | 2 | `53c234e5e8472b6ac51c1ae1cab3fe06fad053beb8ebfd8977b010655bfdd3c3` |
| `status.txt` | 29 | `6cd106b1e6a277b0965b203a7208e3694779301dc0910f2e9990ded0515be119` |
| `stdout.txt` | 0 | `e3b0c44298fc1c149afbf4c8996fbdbb887e6447ecb8248b234d008d9d3f18a` |
| `stderr.txt` | 213 | `9bfdb8d16d4ea9a0b7b68c7272a6fbdbb887e6447ecb8248b234d008d9d3f18a` |

This is an ordinary resumable partial listing outcome, not candidate acceptance or a source
defect. No raw acquisition, candidate acceptance, Gate-2 acceptance, transition, or later work is
authorized by the result.

## Rejected and missing evidence

Record 390 and its publication are incomplete in three material respects:

1. Review 389 required durable Linux start ticks. The runner has no start-tick file, so record
   390's Python PID `463025` is not durably process-identity-bound and its statement that the
   runner contains all required files is rejected.
2. Review 389 required record 390 to contain the exact repository-control and scoped-diff commands,
   outputs, and exit codes. Record 390 contains none of them; the Hermes terminal summary cannot
   substitute for repository-native evidence.
3. Review 389 required final exact-outcome summaries and reviewer actor fields in both control-plane
   files, followed by an exact three-path commit. Commit `0ddb59f5...` contains only record 390.
   `CURRENT_TASK.md` and CEX-002 still name Hermes and describe the completed fresh invocation as
   future work.

The duplicate bullet labels under record 390's `Final actor fields` do not update either actual
control-plane file. The publication is therefore not control-plane complete. No continuation is
authorized until the missing evidence is published and reviewed.

## Evidence-only Hermes authorization

Hermes is authorized only to create
`research/sprint_004/392_CEX002_V2_PARTIAL_RUN_EVIDENCE_AND_CONTROL_PLANE_COMPLETION.md` and update
`docs/handoff/CURRENT_TASK.md` and `tickets/CEX-002.md`.

Record 392 must:

- identify Jr Dev - Hermes as the evidence/publication actor;
- preserve record 390 unchanged;
- state every accepted Review-391 run/candidate/v1 fact without claiming a rerun;
- state that the runner lacks Linux start ticks and does not durably prove the Python PID;
- list the exact seven runner identities above;
- state that commit `0ddb59f5...` contains only record 390 and that the two summaries remained stale;
- contain the exact commands, stdout/stderr, and exit codes for the two fresh publication checks
  below; and
- state that no planner, resume, network, data/candidate mutation, SQLite query, source/test edit,
  cleanup, acquisition, or transition occurred during this correction.

Before repository control, Hermes must set these literal fields:

```text
Next required actor: Lead Quantitative Finance Researcher/Engineer
**Next required actor:** Lead Quantitative Finance Researcher/Engineer
```

Both summaries must report the exact exit-2 partial outcome and incomplete publication correction,
keep CEX-002 and Gate 2 `IN_PROGRESS`, keep next ticket `NONE`, and state that no resume or other
work is authorized. Hermes then runs exactly:

```text
python3 scripts/check_repo_control.py
git diff --check -- docs/handoff/CURRENT_TASK.md research/sprint_004/392_CEX002_V2_PARTIAL_RUN_EVIDENCE_AND_CONTROL_PLANE_COMPLETION.md tickets/CEX-002.md
```

If both exit zero, Hermes stages exactly record 392 plus the two control-plane paths, verifies no
other staged path, commits, pushes `main`, proves `HEAD == origin/main`, and stops. It must not edit
record 390, source/test/CLI, v1, v2, runner files, or unrelated dirty paths. Harness output is a
handoff only; record 392 is required repository evidence.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/391_CEX002_RECORD390_PARTIAL_RUN_ACCEPTANCE_AND_CONTROL_PLANE_EVIDENCE_STOP.md`;
  and
- `tickets/CEX-002.md`.

No implementation/evidence record, source/test, candidate/runner/data, acceptance command, or
unrelated dirty path is included in this reviewer publication.
