# CEX-002 Record-410 Evidence Correction and V3 Continuation Authorization

- **Date:** 2026-09-01
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** accept safe terminal facts; reject publication/count/hash defects; authorize one continuation from the exact pass-2 checkpoint
- **Executing actor:** Jr Dev - Hermes through the installed Hermes one-shot harness
- **Gate 2:** `IN_PROGRESS`
- **Next ticket:** `NONE`

## Accepted publication and bounded execution facts

The reviewer accepts Hermes commit `444c830c389b6278477f9d4db043ae51b600332d` as the exact
three-path publication of record 410 plus the two control-plane paths. `HEAD == origin/main` at
that commit and staging is empty.

The following record-410 facts are accepted:

- the exact code, v1/v2, and pre-existing partial-v3 preflight identities matched Review 409;
- runner `/home/lars/.cache/tmp/tmp.19fBZsEX5Z` launched one planner child, with shell
  `597139@6647225` and planner `597146@6647228` as separate PID/Linux-start-tick identities;
- the runner operated from `2026-09-01T11:03:56Z` through `2026-09-01T11:52:39Z`, captured
  natural exit `2`, and wrote an atomic terminal trailer;
- stderr is the exact 213-byte `stop=resumable_partial` transient-listing report, stdout is empty,
  and neither Hermes nor the runner sent a signal;
- pass 1 completed; pass 2 advanced but remained partial; and
- no locator, receipt, manifest, lineage, candidate, acquisition, transition, later gate, or next
  ticket resulted.

The continuation was not a candidate and consumed Review 409's authorization. The literal runner
location outside `/tmp` is accepted only as recorded execution evidence; it remains a procedural
defect, not a precedent or a reason to discard the checkpoint.

## Rejected record-410 publication claims

Record 410 and its control-plane publication have four material evidence defects:

1. The ticket summary contains the literal placeholder
   `xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` instead of the actual record-410 publication commit.
   That placeholder is false. The actual commit is
   `444c830c389b6278477f9d4db043ae51b600332d`.
2. Record 410 says the working tree has 11 modified and 14 untracked paths unrelated to the
   continuation, then separately excludes `run_continuation_runner.sh`. The exact accounting is
   11 unrelated modified paths plus **13 unrelated untracked paths**, and one additional untracked
   runner-evidence copy, for 14 untracked total.
3. Record 410 reports the terminal checkpoint bytes and private-index hash but omits the required
   terminal checkpoint SHA-256.
4. CURRENT_TASK was not advanced to record 410 and does not list it as a governing document; it
   still describes the now-consumed Review-409 authorization as current.

These claims are rejected and superseded here. Record 410 and its historical ticket section remain
unchanged as deficient evidence; this append-only reviewer correction is controlling. A future
Hermes evidence record must never insert a self-commit placeholder: it cannot know its own commit
hash before commit, so it must refer to the publication without a hash and leave hash acceptance to
the later reviewer.

## Exact terminal resume state

The reviewer independently performed bounded stat/hash/JSON inspection without opening the private
SQLite index. The controlling state is:

| Fact | Exact value |
| --- | --- |
| checkpoint SHA-256 | `c82186e09d560e0f209872e0c21055e137a259f46b088f3e5f2360a473ef1451` |
| checkpoint bytes | `7489213` |
| private-index SHA-256 | `090e55ef831b76ba768e4e3918055b10db61729d0f908bd2b303d3f7f97ef684` |
| private-index bytes | `1085112320` |
| candidate-lock SHA-256 / bytes | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` / `0` |
| page-file count | `3190` |
| publication-file count | `0` |
| pass 1 listing complete / pages | `true` / `2094` |
| pass 1 discovered / completed | `1308` / `1308` |
| pass 1 cursor | `null` |
| pass 2 listing complete / pages | `false` / `1870` |
| pass 2 discovered / completed | `1308` / `1182` |
| pass 2 cursor | `{"continuation_token":null,"prefix":"data/futures/um/daily/metrics/TQQQUSDT/"}` |
| generation plan identity | `8d96db46d5b6df45e4b9c0ba0e45ae9f3688dd88503195fb426e12de827bde22` |
| generation state SHA-256 | `5a5bdc8745c51b1b4b4a15e0de12b7dfa405f8c3a8ae1ba759aa0b6fd7ee33b4` |
| pending identity SHA-256 | `6ac5daa6636092415ce0c01982f05acba4018f65aec85eec67a0db62fe882b61` |

The checkpoint schema contains only the actual cursor object; no `cursor_state` field exists.

## One exact `/tmp` continuation authorization

Exit 2 is the planner's explicit transient, resumable stop. No source, architecture, or financial
semantics changed, so no ADR or developer source drop is required. Hermes is authorized for
exactly one continuation invocation from the exact state above.

Before launch Hermes must:

1. read `AGENTS.md`, CURRENT_TASK, the full CEX-002 ticket, ADR-0033, and Reviews 409-411;
2. prove `HEAD == origin/main` at this review's publication commit, staging empty, and no live
   revision-candidate planner;
3. rehash the five literal code paths and immutable v1/v2 checkpoint/private-index paths exactly
   as specified by Review 405;
4. without opening any SQLite database, prove every current v3 hash, byte, page, publication, and
   checkpoint fact in the table above;
5. prove `/tmp/runner_407_KyKikU/run.sh` still exists at SHA-256
   `d5c4a6b07531b52a95414b9d2a8178de11135e5f4f0b5b09e538ce20748ee820`; and
6. stop and publish a mismatch if any required fact differs.

If preflight passes, Hermes must create the runner with this literal template, not environment-
default `mktemp` behavior:

```text
mktemp -d /tmp/runner_411_XXXXXX
```

It copies `/tmp/runner_407_KyKikU/run.sh` directly into that new directory, verifies the exact
script hash, and launches it once with the repository root and new runner directory arguments
through fully redirected `setsid` plus `nohup`. It must not create, edit, copy, move, or remove any
repository-root runner file. The existing root `run_continuation_runner.sh` remains preserved and
unstaged as evidence.

The runner launches exactly this planner command once as its child:

```text
PYTHONPATH=src .venv/bin/python scripts/research/plan_binance_usdm_gate2_revision_candidate.py
```

The runner must capture separate shell/planner PID and real `/proc/<pid>/stat` field-22 start ticks,
immutable streams/metadata, start/end UTC, exit status, and atomic terminal trailer. It has no
automated cutoff below four hours. After launch Hermes verifies identities and liveness, then
returns without publication and without signaling or killing the runner. Read-only reviewer
observation is permitted. No later Hermes turn may launch a replacement. Natural exit, a runner-
recorded timeout of at least four hours, disappearance, host interruption, or power loss consumes
the continuation.

The planner may only authenticate and extend the fixed partial v3 tree through official Binance S3
ListObjectsV2 requests. It may not reference or mutate v1/v2; GET raw ZIPs; use Coinalyze; edit
source/tests or generation 0; invoke acquisition; clean or replace data; transition; start a later
gate; or launch another invocation.

## Mandatory record 412 and stop

After terminal Hermes may perform only bounded stat/hash/JSON inspection of runner and v3 files;
it may not directly query any real SQLite database. It must publish
`research/sprint_004/412_CEX002_DURABLE_V3_CONTINUATION_RECORD.md` with the exact preflight,
runner, hashes/bytes, complete streams, time/elapsed/allowance, terminal, exactly-once, immutable-
state, checkpoint/pass/cursor/publication, prohibited-action, dirty-path, and completion-or-partial
facts required by Reviews 409 and 411. It must state exactly 13 unrelated untracked paths plus one
separate root runner-evidence copy, use only actual checkpoint fields, record the literal runner
path, and include both pre-launch and terminal checkpoint hashes.

Before repository control Hermes sets both literal top-level actor fields to the reviewer and
writes exact final summaries. It must not place an unknown future commit hash or placeholder in any
file. It then runs only:

```text
python3 scripts/check_repo_control.py
git diff --check -- docs/handoff/CURRENT_TASK.md research/sprint_004/412_CEX002_DURABLE_V3_CONTINUATION_RECORD.md tickets/CEX-002.md
```

If both pass, Hermes commits/pushes exactly record 412 and the two control-plane paths, proves
remote equality, and stops. Candidate/runner/data bytes, the root runner copy, and every unrelated
dirty path remain unstaged. Harness output is a handoff only; only a later repository review may
accept or reject a candidate or authorize acquisition.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/411_CEX002_RECORD410_EVIDENCE_CORRECTION_AND_V3_CONTINUATION_AUTHORIZATION.md`;
  and
- `tickets/CEX-002.md`.

No source/test, implementation evidence, candidate/runner/data, acceptance command, or unrelated
dirty path is included.
