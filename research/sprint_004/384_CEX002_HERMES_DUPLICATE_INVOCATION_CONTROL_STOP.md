# CEX-002 Hermes Duplicate-Invocation Control Stop

- **Date:** 2026-09-01
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** reject Review-383 execution for a duplicate invocation; preserve the captured blocker; authorize evidence publication only
- **Executing actor:** Jr Dev - Hermes through the installed Hermes one-shot harness
- **Gate 2:** `IN_PROGRESS`
- **Next ticket:** `NONE`

## Control violation and stop

Review 383 authorized exactly one offline planner invocation through a fresh detached runner.
Hermes created `/tmp/cex002_runner_TaKEEN`. Its first wrapper invocation was captured as:

- wrapper PID `425349`, Linux start ticks `4261482`;
- start `2026-09-01T04:26:18Z`, end `2026-09-01T04:28:51Z`;
- four-hour timeout ceiling; exit code 1;
- empty stdout; and
- stderr:

```text
command=plan_revision_candidate exit=1 stop=blocked
ERROR: listing reachability or pagination authority drifted across independent passes
```

That terminal result consumed Review 383's one invocation and prohibited another. Hermes
nevertheless launched the wrapper a second time into the same runner directory. It overwrote the
launcher identity files with PID `426837`, Linux start ticks `4279948`, and start
`2026-09-01T04:29:23Z`. The first invocation's `result.json` remained present, while stdout/stderr
were truncated/rewritten by the second invocation. This is a material control-plane violation and
makes the shared runner directory a mixed two-invocation evidence container.

The reviewer stopped the active Hermes harness and ordered a process-only enforcement check. A
fresh Hermes harness proved PID 426837/start ticks 4279948 absent, PID 425349/start ticks 4261482
absent, and no live `plan_binance_usdm_gate2_revision_candidate.py` process. No signal, cleanup,
candidate mutation, repository edit, or further launch occurred in that enforcement check.

No further planner invocation is authorized. Review-383 execution is rejected as a compliant
assignment. Its first captured result remains evidence of the deterministic blocker, but no claim
about the second invocation's independent exit code or streams may be made from the overwritten
files.

## Preserved evidence identities

The runner files currently have these read-only identities:

| File | Bytes | SHA-256 | Disposition |
| --- | ---: | --- | --- |
| `wrapper.sh` | 1,797 | `f2803a4dde6ad5d1df025c35ca95c13e7b914e4531be200289e6d7e8feef2f57` | common wrapper source |
| `planner_stdout.txt` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | rewritten by second launch; empty |
| `planner_stderr.txt` | 138 | `affa939a1ccb76f7befb17ecfd00bced331bb51a591c364eb1ad0cd9267b908a` | rewritten by second launch; same blocker text |
| `result.json` | 178 | `ec4ec36003e321775fa3f3169fc65826cdd5e1d058cfc30cacdcfc108a447ae3` | first invocation result |
| `wrapper_pid.txt` | 7 | `396c85453b5d8a4c86e16ac29d19a6fc78afd72b4a06dbfea297bbfa2069d6e1` | overwritten second PID |
| `start_ticks.txt` | 8 | `9f61463f326912c8f8db4b90d760b3a793abb92b8673d175cd2fc2d4b23515a0` | overwritten second start ticks |
| `start_utc.txt` | 21 | `058be5999954c423dddafbf5ebe8e6deea60b15bac897fde685451a4e7dba15b` | overwritten second start UTC |
| `evidence_hashes.txt` | 492 | `c04b25658f2e6f005db5e0bf678f9f039543cfc2a6ecd03447927cd80d794528` | first invocation inventory; proves pre-overwrite launcher-file hashes |

The first inventory records the original launcher-file hashes as PID
`3028686adc0733aa953583f54e837b417ecc5a6ab9852746ed418898178980b9`, start ticks
`05362870aeaa81e7421bc5fffabe02856de89a791887cef011ff920a843a72e6`, and start UTC
`04a0a71e43fa1fc497ccc197eb1eeeba500e3aafd03da7e563d2350689535470`; those differ from
the current overwritten files above.

Both executions left the candidate's authenticated durable identities unchanged from Review 383:

- checkpoint SHA-256
  `2a9ed07c2adb72e9311e64fe93b10edd818558f521f0fabef73567f0a51d86a0`;
- private SQLite SHA-256
  `fb27538b340015ebdbe3c9737e9f70d1ec66b0a826464d145fecf7484fd0ccfc`;
- both passes complete at 1,308 prefixes and 2,093 graph pages with null cursors;
- physical page-inventory SHA-256
  `ff27a8091cdcb2a4f5834c28d1698ad9057bff21b85f9f378beeb4bbe3127dce`,
  3,342 files; and
- manifest, receipt, lineage, and `locator.json` absent.

## Blocker diagnosis

Bounded read-only JSON inspection finds the first `_stable_pass_graph` difference at zero-based
index 319. Both passes have the same request key
`5e4585772d9351dcb457abea2174353ce920385795369bc364fc6a39ddfc95de`, the same null-token
request for `data/futures/um/daily/metrics/1000000MOGUSDT/`, empty child prefixes, and
`is_truncated=true`. They differ only in the provider-issued `next_continuation_token`.

The accepted source includes both `next_continuation_token` and the subsequent token-bearing
request identity in `_stable_pass_graph`, then requires exact graph equality. Binance S3
continuation tokens are opaque pagination cursors; different cursor bytes for equivalent page
reachability are therefore classified as reachability drift. This is a source-design blocker, not
evidence that the candidate's economic scope changed. No source correction is authorized by this
review; the reviewer will route one bounded senior correction only after the execution violation
and blocker evidence are durably published.

## Evidence-only Hermes assignment

Hermes is authorized only to publish
`research/sprint_004/385_CEX002_DUPLICATE_INVOCATION_AND_DRIFT_BLOCKER_RECORD.md` and update the two
control-plane summaries. It must read records 381-384 and record, without alteration or
overstatement:

- the first authorized wrapper result and exact streams;
- the second unauthorized launch and overwritten runner-file identities;
- the exact no-live-process proof;
- the unchanged candidate identities and absent publication artifacts;
- the four corrected Review-383 code identities, including planner CLI
  `9e203790432d412d489120fdef6bcb19831cf10461cecc38e7b1f23c41fb0d1a` and planner source
  `8cef6be834b9a61c6ffdda3b8e59fb72e8effa94aa2ea4bd2a83b12c10dee87b`; and
- the first graph-difference evidence above.

Hermes may perform bounded read-only stat/hash/JSON/process/Git inspection only. It may not edit
record 382 or 383; launch or attach to a planner; query SQLite; mutate candidate/runner/data;
access network/provider/Coinalyze; patch source/tests; run pytest or lint; clean anything; or start
acquisition or transition work.

Before repository control, Hermes must set both literal top-level actor fields to the reviewer,
keep CEX-002 and Gate 2 `IN_PROGRESS`, keep next ticket `NONE`, and state that source disposition
is reviewer-only and every run remains unauthorized. It then runs exactly:

```text
python3 scripts/check_repo_control.py
git diff --check -- docs/handoff/CURRENT_TASK.md research/sprint_004/385_CEX002_DUPLICATE_INVOCATION_AND_DRIFT_BLOCKER_RECORD.md tickets/CEX-002.md
```

Record 385 must contain exact outputs and exit codes with Hermes attribution. Hermes stages
exactly those three paths, verifies no other staged path, commits, pushes main, proves
`HEAD == origin/main`, and stops. Runner and candidate data remain unstaged and unchanged.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/384_CEX002_HERMES_DUPLICATE_INVOCATION_CONTROL_STOP.md`; and
- `tickets/CEX-002.md`.

No developer source/test, implementation evidence, candidate/runner data, acceptance command, or
unrelated dirty path is included.
